#!/usr/bin/env python3
"""
Регенерация описаний товаров с сохранением структуры biggeek:
  - Берём product-overview с biggeek (h3 + параграф + картинка по сценам Apple).
  - DeepSeek переписывает каждый заголовок (h3) и абзац (своим текстом, на основе
    содержания и характеристик), но количество и порядок секций — как у biggeek.
  - Картинки берём из R2 (image_urls) — позиция соответствует biggeek.

В отличие от старого generate_descriptions.py (общий шаблон 4-5 разделов),
этот скрипт привязывает структуру и иллюстрации к реальному overview biggeek.

Использование:
    python3 scripts/regenerate_descriptions_with_images.py [--limit N] [--slug X] [--concurrency 8]
"""
from __future__ import annotations

import argparse
import html as html_module
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from openai import OpenAI

from lib_biggeek import fetch, load_env, parse_images, parse_jsonld_product, parse_overview_sections, supabase_request

PRINT_LOCK = threading.Lock()


def log(msg: str) -> None:
    with PRINT_LOCK:
        print(msg, flush=True)


def build_prompt(product: dict, sections: list[dict]) -> str:
    """Готовим JSON-input для DeepSeek: список секций с оригинальным h3 и body_text."""
    sections_input = [
        {"index": i, "original_h3": s["h3"], "original_body": s["body_text"]}
        for i, s in enumerate(sections)
    ]

    specs_lines: list[str] = []
    for k, v in (product.get("specs") or {}).items():
        specs_lines.append(f"- {k}: {v}")
    specs_block = "\n".join(specs_lines) if specs_lines else "(нет)"

    sections_json = json.dumps(sections_input, ensure_ascii=False, indent=2)

    return f"""Ты копирайтер интернет-магазина электроники. Тебе дан товар и его описание с сайта-источника, разбитое на секции.

Товар: {product['name']}
Бренд: {product['brand']}
Артикул: {product.get('sku') or '—'}

Характеристики (используй их как факты, не выдумывай новые):
{specs_block}

Исходные секции (массив JSON):
{sections_json}

ЗАДАЧА:
Для каждой секции придумай НОВЫЙ заголовок и перепиши текст СВОИМИ словами. Сохрани суть и факты, но напиши оригинально.

Требования:
- Количество секций — РОВНО столько же, сколько в исходных, и в том же порядке.
- Новые заголовки h3 — живые, кликабельные, не дословные ("Камера" → "Дайте волю своему таланту").
- Текст body_html — 2-4 коротких HTML-параграфа `<p>`, при необходимости списки `<ul><li>`. БЕЗ заголовков внутри body.
- Не выдумывай характеристики, которых нет в списке выше или в исходном тексте.
- Не упоминай магазин-источник, цены, скидки, доставку, гарантию.
- Стиль: профессиональный, без рекламных штампов «лучший в мире», без воды.
- Язык: русский.

Верни СТРОГО валидный JSON-массив (без markdown-обёртки), длина = длина входа:
[
  {{"index": 0, "h3": "...", "body_html": "<p>...</p>"}},
  {{"index": 1, "h3": "...", "body_html": "<p>...</p>"}}
]
""".strip()


def call_deepseek(client: OpenAI, prompt: str) -> list[dict] | None:
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content.strip()
        except Exception as e:
            log(f"  ! DeepSeek attempt {attempt + 1}: {e}")
            continue

        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0].strip()

        # response_format=json_object возвращает объект, иногда оборачивает массив в ключ.
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue

        if isinstance(data, dict):
            # Иногда LLM кладёт массив в ключ типа "sections" или "items"
            for v in data.values():
                if isinstance(v, list):
                    data = v
                    break
        if isinstance(data, list) and data and all(isinstance(x, dict) and "h3" in x and "body_html" in x for x in data):
            return data
    return None


def build_description_html(product_name: str, sections: list[dict], rewritten: list[dict], url_map: dict[str, str]) -> str:
    """
    Собираем итоговый HTML: <h3>{новый}</h3>{новый body}{R2-img если у секции была картинка}.
    Для img: alt = "{product_name} — {original h3}" (оригинальный h3 ближе к содержимому
    картинки, чем переписанный маркетинговый). width/height = 2560×1760 — типичные размеры
    Apple feature shots; браузер использует их как aspect-ratio для предотвращения CLS.
    """
    parts: list[str] = []
    by_index = {r["index"]: r for r in rewritten}
    pname_esc = html_module.escape(product_name)
    for i, src in enumerate(sections):
        rw = by_index.get(i)
        if not rw:
            continue
        h3 = (rw.get("h3") or "").strip()
        body = (rw.get("body_html") or "").strip()
        if not h3 or not body:
            continue
        parts.append(f"<h3>{html_module.escape(h3)}</h3>")
        parts.append(body)
        biggeek_img = src.get("image_url")
        r2_img = url_map.get(biggeek_img) if biggeek_img else None
        if r2_img:
            alt_text = html_module.escape(f"{product_name} — {src['h3']}")
            parts.append(
                f'<figure class="my-5 -mx-2">'
                f'<img src="{r2_img}" alt="{alt_text}" loading="lazy" decoding="async" '
                f'width="2560" height="1760" '
                f'class="w-full h-auto rounded-xl bg-gray-50" />'
                f"</figure>"
            )
    return "\n".join(parts)


def process_product(client: OpenAI, product: dict, idx: int, total: int) -> bool:
    slug = product["slug"]
    if not product.get("biggeek_url"):
        log(f"[{idx}/{total}] {slug}  ⚠ нет biggeek_url")
        return False

    try:
        html = fetch(product["biggeek_url"])
    except Exception as e:
        log(f"[{idx}/{total}] {slug}  ! fetch: {e}")
        return False

    sections = parse_overview_sections(html)
    if not sections:
        log(f"[{idx}/{total}] {slug}  ⚠ нет overview-секций на biggeek")
        return False

    # Воспроизводим тот же порядок, который использовал scrape_biggeek при upsert:
    # parse_images + insert(0, jsonld_image) если её ещё не было.
    biggeek_imgs = parse_images(html, product.get("sku") or "")
    jsonld = parse_jsonld_product(html) or {}
    jsonld_image = jsonld.get("image")
    if jsonld_image:
        jsonld_image = str(jsonld_image)
        if jsonld_image not in biggeek_imgs:
            biggeek_imgs.insert(0, jsonld_image)
    r2_imgs = product.get("image_urls") or []
    url_map = {bg: r2_imgs[i] for i, bg in enumerate(biggeek_imgs) if i < len(r2_imgs)}

    prompt = build_prompt(product, sections)
    rewritten = call_deepseek(client, prompt)
    if not rewritten or len(rewritten) != len(sections):
        log(f"[{idx}/{total}] {slug}  ! DeepSeek не вернул валидный ответ (got {len(rewritten or [])} of {len(sections)})")
        return False

    description_html = build_description_html(product["name"], sections, rewritten, url_map)
    if not description_html:
        log(f"[{idx}/{total}] {slug}  ! пустой результат")
        return False

    try:
        supabase_request(
            "PATCH",
            "g_products",
            body={"description_html": description_html},
            params={"id": f"eq.{product['id']}"},
        )
    except Exception as e:
        log(f"[{idx}/{total}] {slug}  ! не удалось записать: {e}")
        return False
    log(f"[{idx}/{total}] {slug}  ✅ {len(sections)} секций, {len(description_html)} симв.")
    return True


def main():
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--slug", default=None)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--only-empty", action="store_true", help="только товары без description_html")
    args = p.parse_args()

    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if not deepseek_key:
        print("❌ DEEPSEEK_API_KEY не найден")
        sys.exit(1)
    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")

    params: dict[str, Any] = {
        "select": "id,slug,brand,name,sku,specs,biggeek_url,image_urls",
        "order": "id.asc",
    }
    if args.slug:
        params["slug"] = f"eq.{args.slug}"
    if args.only_empty:
        params["description_html"] = "is.null"
    if args.limit:
        params["limit"] = str(args.limit)

    products = supabase_request("GET", "g_products", params=params)
    if not products:
        print("📭 Нет товаров")
        return

    total = len(products)
    print(f"📝 К обработке: {total}, потоков: {args.concurrency}")
    ok = 0
    fail = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(process_product, client, prod, i, total): prod for i, prod in enumerate(products, 1)}
        for f in as_completed(futs):
            if f.result():
                ok += 1
            else:
                fail += 1

    print(f"\n📊 Готово: {ok} ok, {fail} fail")


if __name__ == "__main__":
    main()
