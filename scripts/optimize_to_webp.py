#!/usr/bin/env python3
"""
Конвертирует уже залитые в R2 фото товаров (gadget) в WebP @ 1600px:
1. Скачивает оригинал по URL из image_urls.
2. Прогоняет через Pillow: resize до 1600px, save WebP quality=82.
3. Загружает в R2 с тем же базовым именем, но расширением .webp.
4. Обновляет image_urls в БД.
5. Удаляет оригинальный объект из R2.

Идемпотентно: если URL уже заканчивается на .webp — пропуск.

Использование:
    python3 scripts/optimize_to_webp.py [--slug X] [--limit N] [--dry-run] [--concurrency 6]
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from PIL import Image
from botocore.client import Config
from botocore.exceptions import ClientError

from lib_biggeek import load_env, supabase_request

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


def fetch_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def to_webp(image_bytes: bytes, max_width: int = 1600, quality: int = 82) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode == "P":
        img = img.convert("RGBA")
    if img.mode == "RGBA":
        # WebP с альфа-каналом OK, но Apple feature shots на белом фоне — лучше RGB
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=quality, method=4)
    return out.getvalue()


def key_from_url(url: str, public_base: str) -> str | None:
    if not url.startswith(public_base + "/"):
        return None
    return url[len(public_base) + 1:]


def process_product(client, bucket: str, public_base: str, prod: dict, idx: int, total: int, dry_run: bool) -> bool:
    slug = prod["slug"]
    urls = prod.get("image_urls") or []
    if not urls:
        return True

    new_urls: list[str] = []
    converted = 0
    skipped = 0
    olds_to_delete: list[str] = []
    saved_bytes = 0

    for u in urls:
        if u.lower().endswith(".webp"):
            new_urls.append(u)
            skipped += 1
            continue
        key = key_from_url(u, public_base)
        if not key:
            new_urls.append(u)
            continue

        new_key = key.rsplit(".", 1)[0] + ".webp"
        new_url = f"{public_base}/{new_key}"

        if dry_run:
            log(f"  [dry] {key} → {new_key}")
            new_urls.append(new_url)
            continue

        try:
            raw = fetch_bytes(u)
            webp = to_webp(raw)
        except Exception as e:
            log(f"  ! {slug} {key}: {e}")
            new_urls.append(u)  # оставляем оригинал чтобы не потерять фото
            continue

        try:
            client.put_object(
                Bucket=bucket,
                Key=new_key,
                Body=webp,
                ContentType="image/webp",
                CacheControl="public, max-age=31536000, immutable",
            )
        except ClientError as e:
            log(f"  ! {slug} put_object {new_key}: {e}")
            new_urls.append(u)
            continue

        new_urls.append(new_url)
        olds_to_delete.append(key)
        saved_bytes += max(0, len(raw) - len(webp))
        converted += 1

    if dry_run:
        log(f"[{idx}/{total}] {slug}  [dry] {len(new_urls)} URL'ов")
        return True

    # Сначала обновляем БД, потом удаляем старые объекты — чтобы не потерять рабочее состояние.
    if new_urls != urls:
        upd = supabase_request(
            "PATCH",
            "g_products",
            body={"image_urls": new_urls},
            params={"id": f"eq.{prod['id']}"},
        )
        if upd is None:
            log(f"[{idx}/{total}] {slug}  ! не удалось обновить image_urls, удаление отменено")
            return False

    # Удаляем оригиналы из R2
    for old_key in olds_to_delete:
        try:
            client.delete_object(Bucket=bucket, Key=old_key)
        except ClientError as e:
            log(f"  ! delete {old_key}: {e}")

    saved_mb = saved_bytes / (1024 * 1024)
    log(f"[{idx}/{total}] {slug}  ✅ webp={converted} skip={skipped} delete={len(olds_to_delete)} saved={saved_mb:.1f}MB")
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

    params: dict = {"select": "id,slug,image_urls", "order": "id.asc"}
    if args.slug:
        params["slug"] = f"eq.{args.slug}"
    if args.limit:
        params["limit"] = str(args.limit)

    products = supabase_request("GET", "g_products", params=params)
    products = [p for p in (products or []) if p.get("image_urls")]
    total = len(products)
    print(f"🗜  К конверсии: {total}, потоков: {args.concurrency}, dry-run: {args.dry_run}")

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
