#!/usr/bin/env python3
"""
Генерация уникальных SEO-описаний для товаров в g_products через DeepSeek.

Берёт товары без description_html, передаёт в DeepSeek (name, brand, specs)
с просьбой написать оригинальное описание на 350-500 слов в формате HTML.
Записывает результат в g_products.description_html + meta_description.

Использование:
    python3 scripts/generate_descriptions.py [--limit N] [--force] [--slug SLUG]

    --limit N     обработать не больше N товаров (по умолчанию все без описания)
    --force       перегенерировать даже если description_html уже есть
    --slug X      сгенерировать только для одного товара по slug
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from openai import OpenAI

from lib_biggeek import load_env, supabase_request


def build_prompt(p: dict[str, Any]) -> str:
    specs_lines: list[str] = []
    for k, v in (p.get("specs") or {}).items():
        specs_lines.append(f"- {k}: {v}")
    specs_block = "\n".join(specs_lines) if specs_lines else "(нет)"

    return f"""
Напиши уникальное оригинальное описание товара для интернет-каталога электроники.

Товар: {p['name']}
Бренд: {p['brand']}
Артикул: {p.get('sku') or '—'}

Технические характеристики (используй ТОЛЬКО эти факты — не выдумывай):
{specs_block}

Требования:
- Объём: 350-500 слов.
- Структура: 4-5 разделов с заголовками <h2>. Внутри — <p>, при необходимости <ul><li>.
- Стиль: профессиональный, но живой; не водянисто, без рекламных штампов вроде "лучший в мире".
- НЕ упоминай магазин-источник, цены, скидки, наличие, доставку, гарантию.
- НЕ выдумывай характеристики, которых нет в списке выше.
- Пиши на русском языке.
- ВАЖНО: это должен быть ОРИГИНАЛЬНЫЙ текст, не копия описания с других сайтов.

Структура описания (примерные заголовки, адаптируй под товар):
1. Общее впечатление и для кого товар
2. Дизайн и эргономика (если есть данные о размерах/материалах)
3. Производительность / ключевые технические особенности
4. Камера / экран / аудио (то что важно для категории)
5. Кому подойдёт и кому стоит присмотреться к альтернативам

Верни ТОЛЬКО HTML, без markdown-обёртки. Без DOCTYPE, без <html>, без <body>.
Начинай сразу с первого <h2>.
""".strip()


def build_meta_description(name: str, brand: str, specs: dict[str, str]) -> str:
    """Короткое описание для <meta name='description'>, до 160 символов."""
    parts = [name]
    interesting = []
    for k in ("Объём встроенной памяти", "Объём накопителя", "Диагональ экрана", "Процессор", "Цвет"):
        if specs.get(k):
            interesting.append(f"{k.lower()}: {specs[k]}")
    if interesting:
        parts.append(" · ".join(interesting[:2]))
    parts.append("Купить с актуальной ценой через biggeek.ru.")
    text = ". ".join(parts)
    return text[:157] + "..." if len(text) > 160 else text


PRINT_LOCK = threading.Lock()


def log(msg: str) -> None:
    with PRINT_LOCK:
        print(msg, flush=True)


def process_one(client: OpenAI, prod: dict[str, Any], idx: int, total: int) -> bool:
    prompt = build_prompt(prod)
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        description_html = response.choices[0].message.content.strip()
    except Exception as e:
        log(f"[{idx}/{total}] {prod['slug']}  ! DeepSeek error: {e}")
        return False

    if description_html.startswith("```"):
        description_html = description_html.split("\n", 1)[1]
        if description_html.endswith("```"):
            description_html = description_html.rsplit("```", 1)[0].strip()

    meta_desc = build_meta_description(prod["name"], prod["brand"], prod.get("specs") or {})
    upd = supabase_request(
        "PATCH",
        "g_products",
        body={"description_html": description_html, "meta_description": meta_desc},
        params={"id": f"eq.{prod['id']}"},
    )
    if upd is None:
        log(f"[{idx}/{total}] {prod['slug']}  ! не удалось записать description_html")
        return False
    log(f"[{idx}/{total}] {prod['slug']}  ✅ ({len(description_html)} симв.)")
    return True


def main():
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--slug", default=None)
    p.add_argument("--concurrency", type=int, default=8, help="параллельных потоков (DeepSeek API)")
    args = p.parse_args()

    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if not deepseek_key:
        print("❌ DEEPSEEK_API_KEY не найден в .env.local")
        sys.exit(1)
    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")

    params = {"select": "id,slug,brand,name,sku,specs,description_html", "order": "id.asc"}
    if args.slug:
        params["slug"] = f"eq.{args.slug}"
    elif not args.force:
        params["description_html"] = "is.null"
    if args.limit:
        params["limit"] = str(args.limit)

    products = supabase_request("GET", "g_products", params=params)
    if not products:
        print("📭 Нет товаров для обработки")
        return

    total = len(products)
    print(f"📝 К обработке: {total} товаров, потоков: {args.concurrency}", flush=True)
    ok = 0
    fail = 0

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {
            ex.submit(process_one, client, prod, i, total): prod
            for i, prod in enumerate(products, 1)
        }
        for f in as_completed(futures):
            if f.result():
                ok += 1
            else:
                fail += 1

    print(f"\n📊 Готово: {ok} ok, {fail} fail")


if __name__ == "__main__":
    main()
