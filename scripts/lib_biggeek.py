"""
Утилиты для парсинга biggeek.ru и записи в Supabase.
Используется в scrape_biggeek.py и refresh_prices.py.
Зависимости: только stdlib (urllib, re, json, html).
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import html as html_module
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def load_env() -> None:
    """Подгружает .env.local если соответствующих переменных нет в окружении."""
    env_path = Path(__file__).parent.parent / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def fetch(url: str, timeout: int = 30) -> str:
    """GET HTML-страницу. Возвращает текст или бросает исключение."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


SERVICE_PREFIXES = ("/products/service-",)


def extract_product_links(listing_html: str) -> list[str]:
    """
    Собирает уникальные относительные ссылки /products/... со страницы листинга.
    Отсекает сервисные ссылки (упаковка, гравировка и т.п.).
    """
    links = re.findall(r'href="(/products/[a-z0-9\-]+)"', listing_html)
    seen: list[str] = []
    for l in links:
        if any(l.startswith(p) for p in SERVICE_PREFIXES):
            continue
        if l not in seen:
            seen.append(l)
    return seen


def parse_jsonld_product(page_html: str) -> dict | None:
    """Достаёт JSON-LD Product со страницы карточки biggeek."""
    blocks = re.findall(r'<script type="application/ld\+json">(.+?)</script>', page_html, re.DOTALL)
    for raw in blocks:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Product":
            return data
    return None


def parse_old_price(page_html: str) -> int | None:
    m = re.search(r'<span class="old-price">\s*([\d\s]+?)\s*</span>', page_html)
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group(1))
    return int(digits) if digits else None


def parse_images(page_html: str, sku: str) -> list[str]:
    """
    Картинки товара с biggeek:
    1) Главное фото текущего SKU из /1/870/... в формате `<SKU>-...@2x.{ext}`.
    2) Feature-картинки модели из /4/originals/... — маркетинговые шоты
       Apple (Hero, Camera, Battery, MagSafe, ...), общие для линейки.
       Префикс SKU у них может отличаться (привязан к базовому цвету),
       но визуально они подходят любому SKU модели — берём все.
    """
    raw = re.findall(
        r"(?:https?:)?//images\.biggeek\.ru/[A-Za-z0-9_\-./@]+\.(?:jpg|jpeg|png|webp)",
        page_html,
        re.IGNORECASE,
    )
    main: list[str] = []
    features: list[str] = []
    for u in raw:
        filename = u.rsplit("/", 1)[-1]
        clean = "https:" + u if u.startswith("//") else u
        if "/1/870/" in clean and filename.startswith(f"{sku}-"):
            if clean not in main:
                main.append(clean)
            continue
        if "/4/originals/" in clean:
            if clean not in features:
                features.append(clean)
            continue
    return main + features


def parse_characteristics(page_html: str) -> dict[str, str]:
    """
    Возвращает {название: значение} из блока product-characteristics.
    biggeek рендерит спеки как data-option-name / data-option-value на div'ах.
    """
    start = page_html.find('id="product-characteristics"')
    if start < 0:
        return {}
    # Берём кусок до следующего таба, чтобы не зацепить лишнего
    end = page_html.find('id="product-reviews"', start)
    if end < 0:
        end = page_html.find('id="questions"', start)
    if end < 0:
        end = start + 50000
    block = page_html[start:end]

    pairs = re.findall(
        r'<div[^>]*class="value"[^>]*data-option-name="([^"]+)"[^>]*data-option-value="([^"]*)"',
        block,
    )
    specs: dict[str, str] = {}
    for k, v in pairs:
        key = html_module.unescape(k).strip()
        val = html_module.unescape(v).strip()
        if key and val and key not in specs:
            specs[key] = val
    return specs


def parse_overview_sections(page_html: str) -> list[dict]:
    """
    Парсит описание biggeek (product-overview) на секции вида:
        [
            {"h3": "Заголовок", "body_text": "текст параграфа...", "image_url": "https://..."},
            ...
        ]
    image_url есть не у всех секций (последний h3 на biggeek обычно без картинки).
    URL картинок приводим к абсолютному виду (https://).
    """
    overview = parse_overview(page_html)
    if not overview:
        return []

    # Разбиваем на чанки по тегу <h3>...</h3>
    parts = re.split(r"<h3[^>]*>(.+?)</h3>", overview, flags=re.DOTALL)
    # parts: ['<prefix>', 'title1', 'body1', 'title2', 'body2', ...]
    sections: list[dict] = []
    for i in range(1, len(parts), 2):
        title = html_module.unescape(re.sub(r"<[^>]+>", "", parts[i])).strip()
        body_html = parts[i + 1] if i + 1 < len(parts) else ""

        # Достаём первую картинку из body
        img_m = re.search(r'<img[^>]+src="([^"]+)"', body_html)
        image_url = None
        if img_m:
            raw = img_m.group(1)
            image_url = "https:" + raw if raw.startswith("//") else raw

        # Текст параграфов (без html-тегов) — для подачи в DeepSeek
        body_text = re.sub(r"<[^>]+>", " ", body_html)
        body_text = html_module.unescape(body_text)
        body_text = re.sub(r"\s+", " ", body_text).strip()

        if title and body_text:
            sections.append({"h3": title, "body_text": body_text, "image_url": image_url})
    return sections


def parse_overview(page_html: str) -> str | None:
    """
    Возвращает HTML описания товара из product-overview блока.
    Это сырой контент biggeek — далее прогоняется через DeepSeek для перефраза.
    """
    m = re.search(
        r'<div[^>]*id="product-overview"[^>]*>(.+?)<div[^>]*id="product-characteristics"',
        page_html,
        re.DOTALL,
    )
    if not m:
        return None
    block = m.group(1)
    # Убираем служебные элементы (mob-page-header, кнопки и т.д.)
    block = re.sub(r'<div[^>]*class="mob-page-header"[^>]*>.+?</div>\s*</div>', '', block, flags=re.DOTALL)
    block = re.sub(r'<div[^>]*class="tabs-content__toggle"[^>]*>.+?</div>', '', block, flags=re.DOTALL)
    return block.strip() or None


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_module.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def slug_from_product_url(product_path: str) -> str:
    """`/products/smartfon-apple-iphone-17-256-gb-cernyj-black` → `smartfon-apple-iphone-17-256-gb-cernyj-black`"""
    return product_path.rstrip("/").rsplit("/", 1)[-1]


# ---------- Supabase REST helpers ----------

def supabase_headers() -> dict[str, str]:
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return {
        "Content-Type": "application/json",
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "return=representation",
    }


def supabase_request(method: str, path: str, body=None, params: dict | None = None):
    url = f'{os.environ["NEXT_PUBLIC_SUPABASE_URL"]}/rest/v1/{path}'
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=supabase_headers(), method=method)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="ignore")
            print(f"  ! Supabase {method} {path}: HTTP {e.code} {err}")
            if e.code in (400, 404, 409):
                return None
        except Exception as e:
            print(f"  ! Supabase {method} {path}: {e}")
            time.sleep(2 ** attempt)
    return None


def supabase_upsert(table: str, body, on_conflict: str):
    url = f'{os.environ["NEXT_PUBLIC_SUPABASE_URL"]}/rest/v1/{table}?on_conflict={on_conflict}'
    headers = {**supabase_headers(), "Prefer": "resolution=merge-duplicates,return=representation"}
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="ignore")
            print(f"  ! Supabase upsert {table}: HTTP {e.code} {err}")
            return None
        except Exception as e:
            print(f"  ! Supabase upsert {table}: {e}")
            time.sleep(2 ** attempt)
    return None
