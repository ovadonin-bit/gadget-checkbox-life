#!/usr/bin/env python3
"""
Парсер каталога biggeek.ru → таблица g_products в Supabase.

Использование:
    python3 scripts/scrape_biggeek.py --listing-url <URL> --category-slug <slug> [--limit N] [--publish]

Примеры:
    # Парсим iPhone 17, кладём в категорию "smartphones", не публикуем
    python3 scripts/scrape_biggeek.py \\
        --listing-url https://biggeek.ru/catalog/apple-iphone-17 \\
        --category-slug smartphones \\
        --limit 20

    # То же, но сразу публикуем
    python3 scripts/scrape_biggeek.py \\
        --listing-url https://biggeek.ru/catalog/apple-iphone-17 \\
        --category-slug smartphones \\
        --publish

После запуска товары попадают в g_products с is_published=false по умолчанию.
Дальше прогоняем scripts/generate_descriptions.py для уникального текста,
а потом руками или флагом --publish ставим is_published=true.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from lib_biggeek import (
    extract_product_links,
    fetch,
    load_env,
    parse_characteristics,
    parse_images,
    parse_jsonld_product,
    parse_old_price,
    parse_overview,
    slug_from_product_url,
    strip_tags,
    supabase_request,
    supabase_upsert,
)


def get_category_id(slug: str) -> int | None:
    data = supabase_request("GET", "g_categories", params={"slug": f"eq.{slug}", "select": "id"})
    if not data:
        return None
    return data[0]["id"]


def scrape_product(product_url: str) -> dict | None:
    try:
        html = fetch(product_url)
    except Exception as e:
        print(f"  ! не удалось получить {product_url}: {e}")
        return None

    jsonld = parse_jsonld_product(html)
    if not jsonld:
        print(f"  ! JSON-LD Product не найден на {product_url}")
        return None

    offers = jsonld.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    sku = str(jsonld.get("sku") or "").strip()
    if not sku:
        print(f"  ! пустой sku на {product_url}")
        return None

    name = strip_tags(str(jsonld.get("name") or ""))
    brand = jsonld.get("brand")
    if isinstance(brand, dict):
        brand = brand.get("name")
    brand = strip_tags(str(brand or "Apple"))

    short_desc = strip_tags(str(jsonld.get("description") or ""))

    price = offers.get("price")
    try:
        price_rub = int(price) if price is not None else None
    except (TypeError, ValueError):
        price_rub = None

    availability = offers.get("availability") or ""
    in_stock = availability.endswith("InStock") or availability.endswith("PreOrder")

    old_price = parse_old_price(html)
    images = parse_images(html, sku)
    # Главную из JSON-LD добавляем первой если её ещё нет
    main_img = jsonld.get("image")
    if main_img:
        main_img = str(main_img)
        if main_img not in images:
            images.insert(0, main_img)

    specs = parse_characteristics(html)
    overview_html = parse_overview(html)

    slug = slug_from_product_url(product_url.replace("https://biggeek.ru", "").replace("http://biggeek.ru", ""))

    return {
        "slug": slug,
        "brand": brand,
        "name": name,
        "biggeek_url": product_url,
        "biggeek_product_id": sku,
        "sku": sku,
        "price_rub": price_rub,
        "old_price_rub": old_price,
        "in_stock": in_stock,
        "image_urls": images,
        "specs": specs or None,
        "short_description": short_desc or None,
        "raw_description_html": overview_html,
    }


def upsert_product(parsed: dict, category_id: int, publish: bool) -> int | None:
    """
    Записывает товар в g_products. Описание (description_html) остаётся пустым —
    его сгенерирует generate_descriptions.py через DeepSeek.

    Возвращает id записи или None.
    """
    payload = {
        "slug": parsed["slug"],
        "category_id": category_id,
        "brand": parsed["brand"],
        "name": parsed["name"],
        "biggeek_url": parsed["biggeek_url"],
        "biggeek_product_id": parsed["biggeek_product_id"],
        "sku": parsed["sku"],
        "price_rub": parsed["price_rub"],
        "old_price_rub": parsed["old_price_rub"],
        "in_stock": parsed["in_stock"],
        "image_urls": parsed["image_urls"],
        "specs": parsed["specs"],
        "is_published": publish,
    }
    # Базовый meta_title если ещё не было
    payload["meta_title"] = f'{parsed["name"]} — характеристики и цена'
    if parsed.get("short_description"):
        payload["meta_description"] = parsed["short_description"][:160]

    res = supabase_upsert("g_products", payload, on_conflict="slug")
    if not res:
        return None
    return res[0]["id"]


def write_price_history(product_id: int, price_rub: int | None, in_stock: bool) -> None:
    if price_rub is None:
        return
    supabase_request("POST", "g_price_history", body={
        "product_id": product_id,
        "price_rub": price_rub,
        "in_stock": in_stock,
    })


def main():
    load_env()

    p = argparse.ArgumentParser()
    p.add_argument("--listing-url", required=True, help="URL каталога biggeek, напр. https://biggeek.ru/catalog/apple-iphone-17")
    p.add_argument("--category-slug", required=True, help="slug категории в g_categories (например, smartphones)")
    p.add_argument("--limit", type=int, default=None, help="Сколько товаров обработать (по умолчанию все)")
    p.add_argument("--publish", action="store_true", help="Сразу выставлять is_published=true")
    p.add_argument("--delay", type=float, default=1.0, help="Пауза между запросами в секундах")
    args = p.parse_args()

    category_id = get_category_id(args.category_slug)
    if not category_id:
        print(f"❌ Категория '{args.category_slug}' не найдена в g_categories")
        sys.exit(1)
    print(f"✅ Категория {args.category_slug} → id={category_id}")

    print(f"📥 Загружаю листинг {args.listing_url}")
    listing_html = fetch(args.listing_url)
    links = extract_product_links(listing_html)
    print(f"   найдено {len(links)} ссылок на товары")

    if args.limit:
        links = links[: args.limit]
        print(f"   ограничено до {len(links)} по --limit")

    ok = 0
    fail = 0
    for i, rel in enumerate(links, 1):
        product_url = "https://biggeek.ru" + rel
        print(f"\n[{i}/{len(links)}] {product_url}")
        parsed = scrape_product(product_url)
        if not parsed:
            fail += 1
            continue

        print(f"   {parsed['brand']} · {parsed['name']}")
        print(f"   цена: {parsed['price_rub']} ₽ (стар. {parsed['old_price_rub']}) · фото: {len(parsed['image_urls'])} · спек: {len(parsed['specs'] or {})}")

        product_id = upsert_product(parsed, category_id, args.publish)
        if product_id:
            write_price_history(product_id, parsed["price_rub"], parsed["in_stock"])
            ok += 1
        else:
            fail += 1
        time.sleep(args.delay)

    print(f"\n📊 Готово: {ok} ok, {fail} fail")


if __name__ == "__main__":
    main()
