#!/usr/bin/env python3
"""
Скачивает фото товаров с biggeek.ru, заливает в Cloudflare R2 и обновляет
g_products.image_urls на публичные URL'ы img.gadget.checkbox.life.

Ключ в R2: <sku>/<index>.<ext>  (например 34731/0.jpg, 34731/1.jpg, ...)
Идемпотентно: если объект уже в R2 (HEAD ok) — повторно не льёт, но URL всё
равно подставляет в БД.

Использование:
    python3 scripts/upload_to_r2.py [--limit N] [--slug X] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.request

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from lib_biggeek import USER_AGENT, load_env, supabase_request


def make_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("S3_REGION","ru-1"),
        config=Config(signature_version="s3v4"),
    )


def ext_from_url(url: str) -> str:
    path = url.split("?")[0].rsplit("/", 1)[-1].lower()
    for e in (".jpg", ".jpeg", ".png", ".webp"):
        if path.endswith(e):
            return e.lstrip(".")
    return "jpg"


CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": "https://biggeek.ru/"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def object_exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def upload_product_images(client, bucket: str, public_base: str, sku: str, urls: list[str], dry_run: bool) -> list[str]:
    new_urls: list[str] = []
    for i, src in enumerate(urls):
        ext = ext_from_url(src)
        key = f"{sku}/{i}.{ext}"
        new_url = f"{public_base}/{key}"
        if dry_run:
            print(f"    [dry] {src} → {new_url}")
            new_urls.append(new_url)
            continue
        if object_exists(client, bucket, key):
            print(f"    ⊙ {key} (уже в R2)")
        else:
            try:
                data = download(src)
            except Exception as e:
                print(f"    ! не удалось скачать {src}: {e}")
                continue
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=CONTENT_TYPES.get(ext, "image/jpeg"),
                CacheControl="public, max-age=31536000, immutable",
            )
            print(f"    ↑ {key} ({len(data)} байт)")
        new_urls.append(new_url)
    return new_urls


def main():
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--slug", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    for var in ("S3_ENDPOINT", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET_NAME", "R2_PUBLIC_URL"):
        if not os.environ.get(var):
            print(f"❌ {var} не задан в .env.local")
            sys.exit(1)

    bucket = os.environ["S3_BUCKET_NAME"]
    public_base = os.environ["R2_PUBLIC_URL"].rstrip("/")
    client = make_r2_client()

    params = {"select": "id,slug,sku,image_urls", "order": "id.asc"}
    if args.slug:
        params["slug"] = f"eq.{args.slug}"
    if args.limit:
        params["limit"] = str(args.limit)

    products = supabase_request("GET", "g_products", params=params)
    if not products:
        print("📭 Нет товаров")
        return

    print(f"🚚 К обработке: {len(products)} товаров")
    ok = 0
    for i, prod in enumerate(products, 1):
        sku = prod.get("sku")
        urls = prod.get("image_urls") or []
        print(f"\n[{i}/{len(products)}] {prod['slug']} (sku={sku}, фото={len(urls)})")
        if not sku or not urls:
            print("   ⚠ нет sku или image_urls — пропуск")
            continue
        # Если уже на нашем CDN — нечего грузить
        if all(u.startswith(public_base) for u in urls):
            print("   ✓ уже на R2 CDN — пропуск")
            continue

        new_urls = upload_product_images(client, bucket, public_base, sku, urls, args.dry_run)
        if not new_urls:
            print("   ! не получили ни одного URL")
            continue

        if args.dry_run:
            ok += 1
            continue

        upd = supabase_request(
            "PATCH",
            "g_products",
            body={"image_urls": new_urls},
            params={"id": f"eq.{prod['id']}"},
        )
        if upd is None:
            print("   ! не удалось обновить image_urls в БД")
        else:
            print(f"   ✅ image_urls обновлены ({len(new_urls)} шт.)")
            ok += 1

    print(f"\n📊 Готово: {ok}/{len(products)}")


if __name__ == "__main__":
    main()
