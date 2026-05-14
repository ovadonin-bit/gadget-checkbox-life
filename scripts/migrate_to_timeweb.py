#!/usr/bin/env python3
"""
Миграция данных gadget.checkbox.life: Supabase → Timeweb Cloud PostgreSQL.

Запуск:
  python3 scripts/migrate_to_timeweb.py [--schema-only] [--data-only]
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import psycopg2
import psycopg2.extras

# ── Credentials ──────────────────────────────────────────────────────────────

env_path = Path(__file__).parent.parent / ".env.local"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

SB_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SB_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

TW_HOST = "186.246.4.46"
TW_PORT = 5432
TW_DB   = "gadget"
TW_USER = "gen_user"
TW_PASS = "9qzt=lh1yfAFd)"

SCHEMA_FILE = Path(__file__).parent / "sql" / "schema_timeweb.sql"

# ── Supabase helpers ──────────────────────────────────────────────────────────

def sb_get_all(table: str, page_size: int = 1000) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        url = f"{SB_URL}/rest/v1/{table}?select=*&limit={page_size}&offset={offset}&order=id"
        req = urllib.request.Request(url, headers={
            "apikey": SB_KEY,
            "Authorization": f"Bearer {SB_KEY}",
        })
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    batch = json.loads(r.read())
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(3)
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows

# ── Timeweb helpers ───────────────────────────────────────────────────────────

def tw_connect():
    return psycopg2.connect(
        host=TW_HOST, port=TW_PORT, dbname=TW_DB,
        user=TW_USER, password=TW_PASS, connect_timeout=15,
    )

def apply_schema(conn):
    sql = SCHEMA_FILE.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("✅ Схема создана")

# ── Table import ──────────────────────────────────────────────────────────────

def insert_rows(conn, table: str, rows: list[dict]):
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ",".join(["%s"] * len(cols))
    col_names = ",".join(f'"{c}"' for c in cols)
    sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

    def adapt(v):
        if isinstance(v, dict):
            return psycopg2.extras.Json(v)
        if isinstance(v, list) and v and isinstance(v[0], (dict, list)):
            return psycopg2.extras.Json(v)
        return v

    values = [[adapt(row.get(c)) for c in cols] for row in rows]
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, values, page_size=200)
    conn.commit()
    return len(rows)

def reset_sequences(conn):
    """Reset BIGSERIAL sequences after bulk insert with explicit IDs."""
    seqs = [
        ("g_categories",   "g_categories_id_seq"),
        ("g_products",     "g_products_id_seq"),
        ("g_price_history","g_price_history_id_seq"),
    ]
    with conn.cursor() as cur:
        for table, seq in seqs:
            cur.execute(f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {table}), 1))")
    conn.commit()
    print("✅ Sequences сброшены")

# ── Migration order ───────────────────────────────────────────────────────────

TABLES = ["g_categories", "g_products", "g_price_history"]

def migrate_data(conn):
    for table in TABLES:
        print(f"  📥 {table}...", end=" ", flush=True)
        rows = sb_get_all(table)
        n = insert_rows(conn, table, rows)
        print(f"{n} строк")
    reset_sequences(conn)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema-only", action="store_true")
    ap.add_argument("--data-only",   action="store_true")
    args = ap.parse_args()

    print("🔌 Подключаюсь к Timeweb gadget...")
    conn = tw_connect()
    print("✅ Подключено")

    if not args.data_only:
        print("\n📐 Применяю схему...")
        apply_schema(conn)

    if not args.schema_only:
        print("\n📦 Мигрирую данные из Supabase...")
        migrate_data(conn)

    conn.close()
    print("\n✅ Миграция завершена")

if __name__ == "__main__":
    main()
