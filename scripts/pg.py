#!/usr/bin/env python3
"""
Shared PostgreSQL helper for all auto scripts.
Replaces Supabase REST API calls with direct psycopg2 queries.
"""
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras
import psycopg2.extensions
from psycopg2.extras import Json
from pathlib import Path

# Load .env.local from project root (one level above scripts/)
_env_path = Path(__file__).parent.parent / ".env.local"
for _line in _env_path.read_text().splitlines():
    if "=" in _line and not _line.startswith("#"):
        _k, _, _v = _line.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())

# Auto-serialize dicts and lists as JSON for JSONB columns
psycopg2.extensions.register_adapter(dict, Json)
psycopg2.extensions.register_adapter(list, Json)

_PG = dict(
    host=os.environ["PG_HOST"],
    port=int(os.environ.get("PG_PORT", 5432)),
    dbname=os.environ["PG_DB"],
    user=os.environ["PG_USER"],
    password=os.environ["PG_PASSWORD"],
)


def get_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(**_PG)


def pg_select(
    table: str,
    columns: str = "*",
    where: dict | None = None,
    where_sql: str | None = None,
    limit: int | None = None,
    order: str | None = None,
) -> list[dict]:
    """SELECT from table. where={col: val} for equality; where_sql for raw conditions."""
    parts = [f"SELECT {columns} FROM {table}"]
    params: list = []
    clauses: list[str] = []
    if where:
        for col, val in where.items():
            if val is None:
                clauses.append(f"{col} IS NULL")
            else:
                clauses.append(f"{col} = %s")
                params.append(val)
    if where_sql:
        clauses.append(where_sql)
    if clauses:
        parts.append("WHERE " + " AND ".join(clauses))
    if order:
        parts.append(f"ORDER BY {order}")
    if limit:
        parts.append(f"LIMIT {limit}")
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(" ".join(parts), params)
            return [dict(r) for r in cur.fetchall()]


def pg_insert(table: str, rows: dict | list[dict]) -> list[dict]:
    """INSERT row(s) and return inserted rows."""
    if isinstance(rows, dict):
        rows = [rows]
    if not rows:
        return []
    cols = list(rows[0].keys())
    col_str = ", ".join(cols)
    val_str = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO {table} ({col_str}) VALUES ({val_str}) RETURNING *"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            result = []
            for row in rows:
                cur.execute(sql, [row[c] for c in cols])
                result.extend([dict(r) for r in cur.fetchall()])
        conn.commit()
    return result


def pg_upsert(table: str, rows: dict | list[dict], conflict_column: str | list[str]) -> list[dict]:
    """INSERT ... ON CONFLICT (...) DO UPDATE SET ..."""
    if isinstance(rows, dict):
        rows = [rows]
    if not rows:
        return []
    conflict_cols = [conflict_column] if isinstance(conflict_column, str) else conflict_column
    conflict_str = ", ".join(conflict_cols)
    cols = list(rows[0].keys())
    col_str = ", ".join(cols)
    val_str = ", ".join(["%s"] * len(cols))
    update_str = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c not in conflict_cols)
    sql = (
        f"INSERT INTO {table} ({col_str}) VALUES ({val_str}) "
        f"ON CONFLICT ({conflict_str}) DO UPDATE SET {update_str} RETURNING *"
    )
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            result = []
            for row in rows:
                cur.execute(sql, [row[c] for c in cols])
                result.extend([dict(r) for r in cur.fetchall()])
        conn.commit()
    return result


def pg_update(table: str, where: dict, data: dict) -> None:
    """UPDATE table SET ... WHERE ..."""
    set_parts = [f"{c} = %s" for c in data]
    where_parts = []
    where_params = []
    for col, val in where.items():
        if val is None:
            where_parts.append(f"{col} IS NULL")
        else:
            where_parts.append(f"{col} = %s")
            where_params.append(val)
    sql = (
        f"UPDATE {table} SET {', '.join(set_parts)} "
        f"WHERE {' AND '.join(where_parts)}"
    )
    params = list(data.values()) + where_params
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()


def pg_delete(table: str, where: dict | None = None) -> None:
    """DELETE FROM table WHERE ... (pass where=None to delete all rows)."""
    if not where:
        sql = f"DELETE FROM {table}"
        params = []
    else:
        parts = []
        params = []
        for col, val in where.items():
            if val is None:
                parts.append(f"{col} IS NULL")
            else:
                parts.append(f"{col} = %s")
                params.append(val)
        sql = f"DELETE FROM {table} WHERE {' AND '.join(parts)}"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()


def pg_execute(sql: str, params: list | None = None) -> list[dict]:
    """Run arbitrary SQL and return rows (empty list for non-SELECT)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            try:
                rows = [dict(r) for r in cur.fetchall()]
            except Exception:
                rows = []
        conn.commit()
    return rows
