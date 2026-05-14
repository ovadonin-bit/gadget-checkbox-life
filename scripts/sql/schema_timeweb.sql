-- Schema for gadget.checkbox.life on Timeweb Cloud PostgreSQL
-- Run once on gadget database

CREATE TABLE IF NOT EXISTS g_categories (
  id            BIGSERIAL PRIMARY KEY,
  slug          TEXT UNIQUE NOT NULL,
  name          TEXT NOT NULL,
  parent_id     BIGINT REFERENCES g_categories(id) ON DELETE SET NULL,
  description_html TEXT,
  meta_title    TEXT,
  meta_description TEXT,
  sort_order    INT NOT NULL DEFAULT 0,
  is_published  BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS g_products (
  id                BIGSERIAL PRIMARY KEY,
  slug              TEXT UNIQUE NOT NULL,
  category_id       BIGINT NOT NULL REFERENCES g_categories(id) ON DELETE RESTRICT,
  brand             TEXT NOT NULL,
  name              TEXT NOT NULL,
  biggeek_url       TEXT NOT NULL,
  biggeek_product_id TEXT,
  sku               TEXT,
  price_rub         INT,
  old_price_rub     INT,
  in_stock          BOOLEAN NOT NULL DEFAULT TRUE,
  description_html  TEXT,
  specs             JSONB,
  image_urls        TEXT[] NOT NULL DEFAULT '{}',
  meta_title        TEXT,
  meta_description  TEXT,
  is_published      BOOLEAN NOT NULL DEFAULT FALSE,
  last_checked_at   TIMESTAMPTZ,
  last_seen_at      TIMESTAMPTZ,
  source_status     TEXT NOT NULL DEFAULT 'ok' CHECK (source_status IN ('ok', 'not_found', 'error')),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS g_price_history (
  id          BIGSERIAL PRIMARY KEY,
  product_id  BIGINT NOT NULL REFERENCES g_products(id) ON DELETE CASCADE,
  price_rub   INT NOT NULL,
  in_stock    BOOLEAN NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS g_categories_parent_idx     ON g_categories(parent_id);
CREATE INDEX IF NOT EXISTS g_categories_published_idx  ON g_categories(is_published) WHERE is_published = TRUE;
CREATE INDEX IF NOT EXISTS g_products_category_idx     ON g_products(category_id);
CREATE INDEX IF NOT EXISTS g_products_brand_idx        ON g_products(brand);
CREATE INDEX IF NOT EXISTS g_products_published_idx    ON g_products(is_published) WHERE is_published = TRUE;
CREATE INDEX IF NOT EXISTS g_products_in_stock_idx     ON g_products(in_stock);
CREATE INDEX IF NOT EXISTS g_products_price_idx        ON g_products(price_rub) WHERE price_rub IS NOT NULL;
CREATE INDEX IF NOT EXISTS g_products_last_checked_idx ON g_products(last_checked_at NULLS FIRST);
CREATE INDEX IF NOT EXISTS g_price_history_product_idx ON g_price_history(product_id, captured_at DESC);

CREATE OR REPLACE FUNCTION g_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'g_categories_set_updated_at') THEN
    CREATE TRIGGER g_categories_set_updated_at
      BEFORE UPDATE ON g_categories
      FOR EACH ROW EXECUTE FUNCTION g_set_updated_at();
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'g_products_set_updated_at') THEN
    CREATE TRIGGER g_products_set_updated_at
      BEFORE UPDATE ON g_products
      FOR EACH ROW EXECUTE FUNCTION g_set_updated_at();
  END IF;
END $$;
