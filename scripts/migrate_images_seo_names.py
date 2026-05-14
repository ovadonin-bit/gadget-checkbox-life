#!/usr/bin/env python3
"""
Переименование фото товаров в R2 на SEO-friendly ключи.

Берём оригинальное имя файла с biggeek (например 34730-804Hero17@2x.png),
выделяем описательную часть (hero17), приводим к slug и копируем R2-объект
со старого ключа `<sku>/<N>.<ext>` на новый `<sku>/<slug>.<ext>`. Старые
объекты НЕ удаляем (на случай rollback), просто перестаём ссылаться.

После применения нужно перегенерировать описания, чтобы URL'ы в description_html
указывали на новые ключи.

Использование:
    python3 scripts/migrate_images_seo_names.py [--slug X] [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from lib_biggeek import (
    fetch,
    load_env,
    parse_images,
    parse_jsonld_product,
    supabase_request,
)


PRINT_LOCK = threading.Lock()


def log(msg: str) -> None:
    with PRINT_LOCK:
        print(msg, flush=True)


def make_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def slug_from_filename(filename: str) -> str:
    """
    34730-804Hero17@2x.png            → hero17
    34731-83iphone17_grey@2x.jpg      → iphone17-grey
    34730-27417_camera@2x.png         → camera
    34730-96917__silent@2x.png        → silent
    """
    # отрезаем расширение
    base = filename.rsplit(".", 1)[0]
    # убираем @2x и подобные
    base = re.sub(r"@[0-9.]+x$", "", base)
    # убираем ведущий "SKU-"
    base = re.sub(r"^[0-9]+-", "", base)
    # убираем все ведущие цифры (типа "804")
    base = re.sub(r"^[0-9]+", "", base)
    # подчёркивания → дефисы
    base = base.replace("_", "-")
    # CamelCase → kebab-case (например "MagSafe17" → "mag-safe17")
    base = re.sub(r"(?<=[a-z0-9])([A-Z])", r"-\1", base)
    base = base.lower()
    # только латиница/цифры/дефис
    base = re.sub(r"[^a-z0-9-]+", "-", base)
    base = re.sub(r"-+", "-", base).strip("-")
    return base or "img"


def ext_from_url(url: str) -> str:
    path = url.split("?")[0].rsplit("/", 1)[-1].lower()
    for e in (".jpg", ".jpeg", ".png", ".webp"):
        if path.endswith(e):
            return e.lstrip(".")
    return "jpg"


def build_new_keys(biggeek_urls: list[str], sku: str) -> list[str]:
    """Считает новые ключи для R2: `<sku>/<slug>.<ext>` с дедупом."""
    used: dict[str, int] = {}
    keys: list[str] = []
    for u in biggeek_urls:
        filename = u.rsplit("/", 1)[-1]
        slug = slug_from_filename(filename)
        ext = ext_from_url(u)
        candidate = f"{sku}/{slug}.{ext}"
        if candidate in used:
            used[candidate] += 1
            candidate = f"{sku}/{slug}-{used[candidate]}.{ext}"
        else:
            used[candidate] = 1
        keys.append(candidate)
    return keys


def object_exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def copy_object(client, bucket: str, src_key: str, dst_key: str, content_type: str | None = None) -> bool:
    if object_exists(client, bucket, dst_key):
        return True
    try:
        params = {
            "Bucket": bucket,
            "Key": dst_key,
            "CopySource": {"Bucket": bucket, "Key": src_key},
            "CacheControl": "public, max-age=31536000, immutable",
            "MetadataDirective": "REPLACE",
        }
        if content_type:
            params["ContentType"] = content_type
        client.copy_object(**params)
        return True
    except ClientError as e:
        log(f"  ! copy {src_key} → {dst_key}: {e}")
        return False


CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def process_product(client, bucket: str, public_base: str, prod: dict, idx: int, total: int, dry_run: bool) -> bool:
    slug = prod["slug"]
    sku = prod.get("sku") or ""
    biggeek_url = prod.get("biggeek_url")
    if not sku or not biggeek_url:
        log(f"[{idx}/{total}] {slug}  ⚠ нет sku или biggeek_url")
        return False

    # Воспроизводим тот же порядок, что был при upload_to_r2
    try:
        page = fetch(biggeek_url)
    except Exception as e:
        log(f"[{idx}/{total}] {slug}  ! fetch: {e}")
        return False

    biggeek_imgs = parse_images(page, sku)
    jsonld = parse_jsonld_product(page) or {}
    jsonld_image = jsonld.get("image")
    if jsonld_image:
        jsonld_image = str(jsonld_image)
        if jsonld_image not in biggeek_imgs:
            biggeek_imgs.insert(0, jsonld_image)

    current_image_urls = prod.get("image_urls") or []
    if len(biggeek_imgs) != len(current_image_urls):
        log(f"[{idx}/{total}] {slug}  ⚠ кол-во не совпадает: biggeek={len(biggeek_imgs)} db={len(current_image_urls)}")
        # продолжаем по min длине — лучше что-то, чем ничего
    n = min(len(biggeek_imgs), len(current_image_urls))

    new_keys = build_new_keys(biggeek_imgs[:n], sku)
    new_urls: list[str] = []
    ops = 0
    for i in range(n):
        old_url = current_image_urls[i]
        # извлекаем старый ключ из URL `https://img.gadget.checkbox.life/<key>`
        if old_url.startswith(public_base + "/"):
            old_key = old_url[len(public_base) + 1:]
        else:
            log(f"  ! не наш CDN-URL: {old_url}")
            continue
        new_key = new_keys[i]
        new_url = f"{public_base}/{new_key}"
        if old_key == new_key:
            new_urls.append(new_url)
            continue

        ext = new_key.rsplit(".", 1)[-1]
        if dry_run:
            log(f"  [dry] {old_key} → {new_key}")
        else:
            if not copy_object(client, bucket, old_key, new_key, CONTENT_TYPES.get(ext, "image/jpeg")):
                log(f"  ! пропуск {old_key}")
                new_urls.append(old_url)
                continue
            ops += 1
        new_urls.append(new_url)

    if dry_run:
        log(f"[{idx}/{total}] {slug}  [dry] {len(new_urls)} URL'ов")
        return True

    upd = supabase_request(
        "PATCH",
        "g_products",
        body={"image_urls": new_urls},
        params={"id": f"eq.{prod['id']}"},
    )
    if upd is None:
        log(f"[{idx}/{total}] {slug}  ! не удалось обновить image_urls")
        return False
    log(f"[{idx}/{total}] {slug}  ✅ copy={ops}, urls={len(new_urls)}")
    return True


def main():
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--slug", default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--concurrency", type=int, default=6)
    args = p.parse_args()

    for v in ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME", "R2_PUBLIC_URL"):
        if not os.environ.get(v):
            print(f"❌ {v} не задан")
            sys.exit(1)

    bucket = os.environ["R2_BUCKET_NAME"]
    public_base = os.environ["R2_PUBLIC_URL"].rstrip("/")
    client = make_r2_client()

    params = {"select": "id,slug,sku,biggeek_url,image_urls", "order": "id.asc"}
    if args.slug:
        params["slug"] = f"eq.{args.slug}"
    if args.limit:
        params["limit"] = str(args.limit)

    products = supabase_request("GET", "g_products", params=params)
    if not products:
        print("📭 Нет товаров")
        return

    total = len(products)
    print(f"🔄 К миграции: {total}, потоков: {args.concurrency}, dry-run: {args.dry_run}")
    ok = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {
            ex.submit(process_product, client, bucket, public_base, prod, i, total, args.dry_run): prod
            for i, prod in enumerate(products, 1)
        }
        for f in as_completed(futs):
            if f.result():
                ok += 1
    print(f"\n📊 Готово: {ok}/{total}")


if __name__ == "__main__":
    main()
