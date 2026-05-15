#!/opt/homebrew/bin/python3
"""
Батч-парсинг нескольких категорий biggeek.ru с поддержкой пагинации.

Запуск:
  python3 scripts/batch_scrape.py [--dry-run] [--delay 1.0]
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.lib_biggeek import extract_product_links, fetch, load_env, supabase_request
from scripts.scrape_biggeek import get_category_id, scrape_product, upsert_product

# ── Что парсим ────────────────────────────────────────────────────────────────
# (category_slug, [listing_urls])  — порядок = приоритет
PLAN = [
    # Дополняем существующие категории
    ("tablets",     [
        "https://biggeek.ru/catalog/apple-ipad",          # ~312 iPad
        "https://biggeek.ru/catalog/planshety-samsung",   # ~104 Samsung
        "https://biggeek.ru/catalog/planshety-xiaomi",    # ~52 Xiaomi
    ]),
    ("laptops",     [
        "https://biggeek.ru/catalog/noutbuki-apple",      # ~442 MacBook
    ]),
    ("smartphones", [
        "https://biggeek.ru/catalog/smartfony-samsung",   # ~286
        "https://biggeek.ru/catalog/cmartfony-xiaomi",    # ~52
        "https://biggeek.ru/catalog/google-pixel",        # ~78
        "https://biggeek.ru/catalog/kupit-oneplus",       # ~78
        "https://biggeek.ru/catalog/huawei-honor",        # ~78
    ]),
    ("watches",     [
        "https://biggeek.ru/catalog/umnye-chasy-garmin",  # ~156
        "https://biggeek.ru/catalog/umnye-chasy-samsung", # ~11
    ]),
    ("appliances",  [
        "https://biggeek.ru/catalog/dyson",               # ~130
    ]),
    # Новые категории
    ("gaming",      [
        "https://biggeek.ru/catalog/sony-playstation",    # ~19
        "https://biggeek.ru/catalog/microsoft-xbox",      # ~8
        "https://biggeek.ru/catalog/nintendo-switch",     # ~7
        "https://biggeek.ru/catalog/steam-deck",
        "https://biggeek.ru/catalog/asus-rog-ally",
    ]),
    ("lego",        [
        "https://biggeek.ru/catalog/konstruktory-lego",   # ~286
    ]),
]


def collect_all_links(base_url: str, delay: float) -> list[str]:
    """Собираем ссылки на товары со всех страниц категории."""
    all_links: list[str] = []
    seen: set[str] = set()

    # Узнаём количество страниц с первой страницы
    html = fetch(base_url)
    page_nums = [int(x) for x in re.findall(r'[?&]page=(\d+)', html) if int(x) < 500]
    max_page = max(page_nums) if page_nums else 1

    # Страница 1 уже загружена
    for link in extract_product_links(html):
        if link not in seen:
            seen.add(link)
            all_links.append(link)

    # Остальные страницы
    for page in range(2, max_page + 1):
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}page={page}"
        try:
            html = fetch(url)
            for link in extract_product_links(html):
                if link not in seen:
                    seen.add(link)
                    all_links.append(link)
        except Exception as e:
            print(f"    ⚠ стр.{page}: {e}")
        time.sleep(delay)

    return all_links


def get_existing_biggeek_urls() -> set[str]:
    """Уже сохранённые biggeek_url из БД."""
    data = supabase_request("GET", "g_products", params={"select": "biggeek_url"})
    return {r["biggeek_url"] for r in (data or []) if r.get("biggeek_url")}


def main() -> None:
    load_env()

    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Показать план без парсинга")
    p.add_argument("--delay", type=float, default=0.8, help="Пауза между запросами (сек)")
    p.add_argument("--category", default=None, help="Запустить только эту категорию")
    args = p.parse_args()

    plan = [(s, u) for s, u in PLAN if not args.category or s == args.category]

    if args.dry_run:
        print("📋 План парсинга:")
        for slug, urls in plan:
            print(f"\n  [{slug}]")
            for u in urls:
                print(f"    {u}")
        return

    existing = get_existing_biggeek_urls()
    print(f"📦 Уже в БД: {len(existing)} товаров\n")

    total_new = 0

    for cat_slug, listing_urls in plan:
        cat_id = get_category_id(cat_slug)
        if not cat_id:
            print(f"❌ Категория '{cat_slug}' не найдена в g_categories")
            continue

        print(f"\n{'═'*60}")
        print(f"📂 [{cat_slug}]  category_id={cat_id}")

        for listing_url in listing_urls:
            print(f"\n  📥 {listing_url}")
            try:
                links = collect_all_links(listing_url, args.delay)
            except Exception as e:
                print(f"    ❌ Ошибка загрузки листинга: {e}")
                continue

            # Фильтруем уже существующие
            new_links = [
                l for l in links
                if f"https://biggeek.ru{l}" not in existing
            ]
            print(f"    Найдено: {len(links)}, новых: {len(new_links)}")

            ok = fail = 0
            for i, rel in enumerate(new_links, 1):
                product_url = "https://biggeek.ru" + rel
                print(f"\n  [{i}/{len(new_links)}] {product_url}")
                parsed = scrape_product(product_url)
                if not parsed:
                    fail += 1
                    time.sleep(args.delay)
                    continue

                result = upsert_product(parsed, cat_id, publish=True)
                if result:
                    ok += 1
                    existing.add(product_url)
                    total_new += 1
                else:
                    fail += 1
                time.sleep(args.delay)

            print(f"\n  ✅ {ok} добавлено, ❌ {fail} ошибок")

    print(f"\n{'═'*60}")
    print(f"🎉 Итого новых товаров: {total_new}")
    print("Следующий шаг: python3 scripts/regenerate_descriptions_with_images.py")


if __name__ == "__main__":
    main()
