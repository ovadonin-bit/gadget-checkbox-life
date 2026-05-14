-- Колонки для отслеживания синхронизации с biggeek.ru.
-- Применить через Supabase SQL Editor.

ALTER TABLE g_products
  ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_seen_at    TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS source_status   TEXT NOT NULL DEFAULT 'ok';

-- ok | not_found | error
ALTER TABLE g_products
  ADD CONSTRAINT g_products_source_status_chk
  CHECK (source_status IN ('ok', 'not_found', 'error'));

CREATE INDEX IF NOT EXISTS g_products_last_checked_at_idx
  ON g_products (last_checked_at NULLS FIRST);
