#!/usr/bin/env python3
"""
Лёгкий обходчик: проходит по существующим g_products, парсит у biggeek.ru
только цену/наличие, пишет в g_price_history ТОЛЬКО при изменении.

Также обновляет на товаре: price_rub, old_price_rub, in_stock,
last_checked_at, last_seen_at, source_status.

Использование:
    python3 scripts/refresh_prices.py [--limit N] [--slug X] [--delay 0.5]

Запускается на Vercel cron каждые 6 часов.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from lib_biggeek import (
    fetch,
    load_env,
    parse_jsonld_product,
    parse_old_price,
    supabase_request,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_current_state(biggeek_url: str) -> tuple[str, dict]:
    """
    Возвращает (source_status, payload). Payload содержит price_rub, old_price_rub,
    in_stock — если status != 'ok', payload пустой.
    """
    try:
        html = fetch(biggeek_url)
    except Exception as e:
        msg = str(e)
        if "404" in msg or "HTTP Error 404" in msg:
            return "not_found", {}
        print(f"  ! fetch error: {e}")
        return "error", {}

    jsonld = parse_jsonld_product(html)
    if not jsonld:
        return "error", {}

    offers = jsonld.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    try:
        price_rub = int(offers.get("price")) if offers.get("price") is not None else None
    except (TypeError, ValueError):
        price_rub = None

    availability = offers.get("availability") or ""
    in_stock = availability.endswith("InStock") or availability.endswith("PreOrder")
    old_price = parse_old_price(html)

    return "ok", {
        "price_rub": price_rub,
        "old_price_rub": old_price,
        "in_stock": in_stock,
    }


def main():
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--slug", default=None)
    p.add_argument("--delay", type=float, default=0.5)
    args = p.parse_args()

    params = {
        "select": "id,slug,biggeek_url,price_rub,old_price_rub,in_stock,source_status",
        "order": "last_checked_at.asc.nullsfirst",
    }
    if args.slug:
        params["slug"] = f"eq.{args.slug}"
    if args.limit:
        params["limit"] = str(args.limit)

    products = supabase_request("GET", "g_products", params=params)
    if not products:
        print("📭 Нет товаров")
        return

    print(f"🔄 К обновлению: {len(products)} товаров")
    checked = 0
    price_changed = 0
    stock_changed = 0
    not_found = 0
    errors = 0

    for i, prod in enumerate(products, 1):
        print(f"\n[{i}/{len(products)}] {prod['slug']}")
        if not prod.get("biggeek_url"):
            print("   ⚠ нет biggeek_url — пропуск")
            continue

        status, new_state = fetch_current_state(prod["biggeek_url"])
        checked += 1

        patch: dict = {
            "last_checked_at": now_iso(),
            "source_status": status,
        }

        if status == "ok":
            patch["last_seen_at"] = patch["last_checked_at"]
            new_price = new_state.get("price_rub")
            new_old = new_state.get("old_price_rub")
            new_stock = new_state.get("in_stock")
            old_price = prod.get("price_rub")
            old_stock = prod.get("in_stock")

            patch["price_rub"] = new_price
            patch["old_price_rub"] = new_old
            patch["in_stock"] = new_stock

            changed = (new_price != old_price) or (new_stock != old_stock)
            if changed and new_price is not None:
                supabase_request("POST", "g_price_history", body={
                    "product_id": prod["id"],
                    "price_rub": new_price,
                    "in_stock": new_stock,
                })
                if new_price != old_price:
                    price_changed += 1
                    print(f"   💰 {old_price} → {new_price} ₽")
                if new_stock != old_stock:
                    stock_changed += 1
                    print(f"   📦 in_stock {old_stock} → {new_stock}")
            else:
                print(f"   ✓ без изменений ({new_price} ₽)")
        elif status == "not_found":
            not_found += 1
            print("   🚫 404 — товар снят")
        else:
            errors += 1
            print("   ⚠ ошибка")

        upd = supabase_request(
            "PATCH",
            "g_products",
            body=patch,
            params={"id": f"eq.{prod['id']}"},
        )
        if upd is None:
            print("   ! не удалось записать обновления")

        time.sleep(args.delay)

    print(f"\n📊 Готово: проверено {checked}, цена↑↓ {price_changed}, stock↑↓ {stock_changed}, 404 {not_found}, errors {errors}")
    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
