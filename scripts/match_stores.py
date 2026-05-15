#!/opt/homebrew/bin/python3
"""
Шаг 1: Парсим каталоги Hi Store и Билайн, сохраняем все товары.
Шаг 2: Fuzzy-матчинг с нашими товарами из БД.
Шаг 3: Экспортируем CSV для проверки, затем заливаем в БД.

Запуск:
  python3 scripts/match_stores.py --scrape      # шаг 1: парсинг каталогов
  python3 scripts/match_stores.py --match       # шаг 2+3: матчинг + CSV
  python3 scripts/match_stores.py --apply       # шаг 4: залить подтверждённые в БД
  python3 scripts/match_stores.py --scrape --match  # сразу оба
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_biggeek import fetch, load_env
from pg import get_conn

# ── Константы ──────────────────────────────────────────────────────────────

HISTORE_CATEGORIES = [
    "https://hi-stores.ru/catalog/iphone/",
    "https://hi-stores.ru/catalog/ipad/",
    "https://hi-stores.ru/catalog/mac/",
    "https://hi-stores.ru/catalog/airpods/",
    "https://hi-stores.ru/catalog/apple-watch/",
    "https://hi-stores.ru/catalog/apple-tv/",
]

BEELINE_CATEGORIES = [
    "https://moskva.beeline.ru/shop/catalog/telefony/smartfony/",
    "https://moskva.beeline.ru/shop/catalog/planshety/planshety-3/",
    "https://moskva.beeline.ru/shop/catalog/audio/naushniki/",
    "https://moskva.beeline.ru/shop/catalog/gadzhety/umnye-chasy-i-braslety/",
    "https://moskva.beeline.ru/shop/catalog/kompiuternaia-tekhnika/noutbuki/",
]

HISTORE_BASE = "https://hi-stores.ru"
BEELINE_BASE = "https://moskva.beeline.ru"
HISTORE_DEEPLINK = "https://wpmsx.com/g/hwysxaae1b7ad04f0a593a4ea8cf25/?erid=2bL9aMPo2e49hMef4piUAotQ6a"
BEELINE_DEEPLINK = "https://rcpsj.com/g/exxsgtkm6c7ad04f0a59dbadac95b8/?erid=2bL9aMPo2e49hMef4phUdXKkvx"

HISTORE_CATALOG_FILE = Path(__file__).parent / "histore_catalog.json"
BEELINE_CATALOG_FILE = Path(__file__).parent / "beeline_catalog.json"
MATCH_CSV = Path(__file__).parent / "store_matches.csv"

DELAY = 0.6
MATCH_THRESHOLD = 86  # минимальный % совпадения (5/6 = 83% отсекает Pro←ProMax)

# ── Нормализация названий ───────────────────────────────────────────────────

# Таблица замен единиц и мусорных слов
_NORM_RE = [
    (re.compile(r'\bсмартфон\b|\bпланшет\b|\bноутбук\b|\bнаушники\b|\bчасы\b', re.I), ''),
    (re.compile(r'\b(smartfon|planshet|noutbuk|naushniki|chasy)\b', re.I), ''),  # Beeline slug transliterations
    (re.compile(r'\b(\d+)\s*гб\b', re.I), r'\1gb'),
    (re.compile(r'\b(\d+)\s*тб\b', re.I), r'\1tb'),
    (re.compile(r'\b(\d+)\s*мп\b', re.I), r'\1mp'),
    (re.compile(r'\b(nano|micro|esim|plusesim|nano\+esim|dual\s*sim|без\s*rustore|bez\s*rustore|rustore|bez)\b', re.I), ''),
    (re.compile(r'\b[A-Z0-9]{6,}\b'), ''),   # артикулы заглавными (MLNC3AHA)
    (re.compile(r'\b(?=[a-z]*[0-9])[a-z][a-z0-9]{5,}\b'), ''),  # артикулы строчными (mg8g4kha)
    (re.compile(r'[+/|()[\]«»""„]'), ' '),
    (re.compile(r'\s{2,}'), ' '),
]

_COLORS_RU = re.compile(
    r'\b(черный|чёрный|белый|синий|голубой|зеленый|зелёный|красный|желтый|жёлтый|'
    r'фиолетовый|розовый|серый|серебристый|золотой|оранжевый|бежевый|коричневый|'
    r'насыщенный|туманно|туманный|шалфейный|лавандовый|космический|натуральный|'
    r'глубокий|светлый|тёмный|темный|снежный|кремовый|пустынный|'
    r'midnight|starlight|natural|black|white|blue|green|red|purple|pink|silver|gold|'
    r'orange|cosmic|deep|light|space|desert|titanium|lavender|sage|teal|ultramarine|'
    r'mist|slate|storm|sand|clay)\b',
    re.I,
)


def normalize(name: str) -> str:
    s = name.lower().strip()
    for pattern, repl in _NORM_RE:
        s = pattern.sub(repl, s)
    s = _COLORS_RU.sub('', s)
    s = re.sub(r'\s{2,}', ' ', s).strip()
    return s


def slug_to_name(slug: str) -> str:
    """Билайн/Histore: slug → читаемое название."""
    return slug.replace('-', ' ').replace('_', ' ')


# ── Deeplink-хелпер ────────────────────────────────────────────────────────

def make_deeplink(base: str, product_url: str) -> str:
    return f"{base}&ulp={urllib.parse.quote(product_url, safe='')}"


# ── Парсинг Hi Store ───────────────────────────────────────────────────────

def scrape_histore() -> list[dict]:
    """Возвращает [{name, url, norm}] для всех товаров Hi Store."""
    import json
    products: list[dict] = []
    seen: set[str] = set()

    product_re = re.compile(
        r'href="(/catalog/[a-z0-9/_-]+/apple-[a-z0-9_-]+/)"',
    )

    for cat_url in HISTORE_CATEGORIES:
        print(f"  Hi Store: {cat_url}")
        page = 1
        while True:
            url = cat_url if page == 1 else f"{cat_url}?PAGEN_1={page}"
            try:
                html = fetch(url)
            except Exception as e:
                print(f"    ⚠ {e}")
                break

            # Ищем ссылки на конкретные товары (содержат "apple-")
            found = product_re.findall(html)
            new = list(dict.fromkeys(u for u in found if u not in seen))
            if not new:
                break

            for rel in new:
                seen.add(rel)
                # Извлекаем название из URL-пути
                slug = rel.rstrip('/').split('/')[-1]
                name = slug_to_name(slug)
                full_url = HISTORE_BASE + rel
                products.append({
                    "name": name,
                    "url": full_url,
                    "norm": normalize(name),
                })

            print(f"    стр.{page}: +{len(new)} товаров (итого {len(products)})")
            page += 1
            time.sleep(DELAY)

    HISTORE_CATALOG_FILE.write_text(
        json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  ✅ Hi Store: {len(products)} товаров → {HISTORE_CATALOG_FILE.name}")
    return products


# ── Парсинг Билайн ─────────────────────────────────────────────────────────

def scrape_beeline() -> list[dict]:
    import json
    products: list[dict] = []
    seen: set[str] = set()

    # Ищем /shop/details/{slug}/ (без подпутей)
    detail_re = re.compile(r'/shop/details/([a-z0-9_-]+)/')

    for cat_url in BEELINE_CATEGORIES:
        print(f"  Beeline: {cat_url}")
        page = 1
        while True:
            url = cat_url if page == 1 else f"{cat_url}?page={page}"
            try:
                html = fetch(url)
            except Exception as e:
                print(f"    ⚠ {e}")
                break

            slugs = detail_re.findall(html)
            new = [s for s in slugs if s not in seen]
            if not new:
                break

            for slug in new:
                seen.add(slug)
                name = slug_to_name(slug)
                full_url = f"{BEELINE_BASE}/shop/details/{slug}/"
                products.append({
                    "name": name,
                    "url": full_url,
                    "norm": normalize(name),
                })

            print(f"    стр.{page}: +{len(new)} товаров (итого {len(products)})")
            page += 1
            time.sleep(DELAY)

    BEELINE_CATALOG_FILE.write_text(
        json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  ✅ Beeline: {len(products)} товаров → {BEELINE_CATALOG_FILE.name}")
    return products


# ── Fuzzy-матчинг ──────────────────────────────────────────────────────────

def fuzzy_score(a: str, b: str) -> int:
    """Простой token-based similarity без внешних зависимостей."""
    ta = set(a.split())
    tb = set(b.split())
    if not ta or not tb:
        return 0
    inter = ta & tb
    return int(100 * len(inter) / max(len(ta), len(tb)))


def best_match(norm_query: str, catalog: list[dict]) -> tuple[dict | None, int]:
    best, best_score = None, 0
    for item in catalog:
        s = fuzzy_score(norm_query, item["norm"])
        if s > best_score:
            best, best_score = item, s
    return best, best_score


def run_matching(
    histore: list[dict],
    beeline: list[dict],
) -> None:
    import json

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, slug, brand, name FROM g_products
        WHERE is_published = true
        ORDER BY id
    """)
    our_products = cur.fetchall()
    conn.close()

    rows = []
    for (pid, slug, brand, name) in our_products:
        norm = normalize(name)

        # Hi Store — только Apple
        hi_url, hi_score = '', 0
        if brand and brand.lower() == 'apple':
            item, hi_score = best_match(norm, histore)
            if item and hi_score >= MATCH_THRESHOLD:
                hi_url = item["url"]

        # Beeline — все бренды
        bl_url, bl_score = '', 0
        item, bl_score = best_match(norm, beeline)
        if item and bl_score >= MATCH_THRESHOLD:
            bl_url = item["url"]

        if hi_url or bl_url:
            rows.append({
                "id": pid,
                "slug": slug,
                "name": name,
                "histore_url": hi_url,
                "hi_score": hi_score,
                "histore_deeplink": make_deeplink(HISTORE_DEEPLINK, hi_url) if hi_url else '',
                "beeline_url": bl_url,
                "bl_score": bl_score,
                "beeline_deeplink": make_deeplink(BEELINE_DEEPLINK, bl_url) if bl_url else '',
            })

    with MATCH_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "slug", "name",
            "histore_url", "hi_score", "histore_deeplink",
            "beeline_url", "bl_score", "beeline_deeplink",
        ])
        writer.writeheader()
        writer.writerows(rows)

    matched_hi = sum(1 for r in rows if r["histore_url"])
    matched_bl = sum(1 for r in rows if r["beeline_url"])
    print(f"\n✅ Матчинг завершён: {len(rows)} товаров")
    print(f"  Hi Store:  {matched_hi} совпадений")
    print(f"  Beeline:   {matched_bl} совпадений")
    print(f"  CSV:       {MATCH_CSV}")


# ── Заливка в БД ───────────────────────────────────────────────────────────

def run_apply() -> None:
    if not MATCH_CSV.exists():
        sys.exit(f"❌ Нет файла {MATCH_CSV}. Сначала запусти --match")

    conn = get_conn()
    cur = conn.cursor()

    updated = 0
    with MATCH_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            hi = row["histore_url"].strip()
            bl = row["beeline_url"].strip()
            if not hi and not bl:
                continue
            cur.execute("""
                UPDATE g_products
                SET histore_url = NULLIF(%s,''), beeline_url = NULLIF(%s,'')
                WHERE id = %s
            """, (hi or None, bl or None, int(row["id"])))
            updated += 1

    conn.commit()
    conn.close()
    print(f"✅ Обновлено {updated} товаров в БД")


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--scrape", action="store_true", help="Парсинг каталогов магазинов")
    p.add_argument("--match",  action="store_true", help="Fuzzy-матчинг + экспорт CSV")
    p.add_argument("--apply",  action="store_true", help="Залить CSV в БД")
    args = p.parse_args()

    if not any([args.scrape, args.match, args.apply]):
        p.print_help()
        return

    histore, beeline = [], []

    if args.scrape:
        import json
        print("\n📦 Парсим Hi Store...")
        histore = scrape_histore()
        print("\n📦 Парсим Beeline...")
        beeline = scrape_beeline()
    elif args.match:
        import json
        if HISTORE_CATALOG_FILE.exists():
            histore = json.loads(HISTORE_CATALOG_FILE.read_text(encoding="utf-8"))
            print(f"📂 Hi Store: загружено {len(histore)} из кэша")
        if BEELINE_CATALOG_FILE.exists():
            beeline = json.loads(BEELINE_CATALOG_FILE.read_text(encoding="utf-8"))
            print(f"📂 Beeline: загружено {len(beeline)} из кэша")

    if args.match:
        print("\n🔍 Матчинг...")
        run_matching(histore, beeline)

    if args.apply:
        print("\n💾 Заливаем в БД...")
        run_apply()


if __name__ == "__main__":
    main()
