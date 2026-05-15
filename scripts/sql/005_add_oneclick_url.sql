-- Добавляем oneclick_url в таблицу g_products.
-- Запускать однократно на боевой БД.

ALTER TABLE g_products
  ADD COLUMN IF NOT EXISTS oneclick_url TEXT DEFAULT NULL;
