import postgres from 'postgres'
import type { Category, Product } from '@/types/db'

const sql = postgres({
  host: process.env.PG_HOST!,
  port: Number(process.env.PG_PORT ?? 5432),
  database: process.env.PG_DB!,
  username: process.env.PG_USER!,
  password: process.env.PG_PASSWORD!,
  ssl: false,
  max: 1,
  idle_timeout: 30,
  connect_timeout: 15,
})

export { sql }

// ─── Categories ──────────────────────────────────────────────────────────────

export async function getPublishedRootCategories(): Promise<Pick<Category, 'id' | 'slug' | 'name' | 'sort_order'>[]> {
  const rows = await sql`
    SELECT id, slug, name, sort_order
    FROM g_categories
    WHERE is_published = true AND parent_id IS NULL
    ORDER BY sort_order ASC
  `
  return rows as unknown as Pick<Category, 'id' | 'slug' | 'name' | 'sort_order'>[]
}

export async function getCategoryBySlug(slug: string): Promise<Category | null> {
  const rows = await sql`
    SELECT * FROM g_categories
    WHERE slug = ${slug} AND is_published = true
    LIMIT 1
  `
  return (rows[0] ?? null) as Category | null
}

export async function getCategoryById(id: number): Promise<Category | null> {
  const rows = await sql`
    SELECT * FROM g_categories WHERE id = ${id} LIMIT 1
  `
  return (rows[0] ?? null) as Category | null
}

export async function getAllPublishedCategorySlugs(): Promise<{ slug: string; updated_at: string }[]> {
  const rows = await sql`
    SELECT slug, updated_at FROM g_categories WHERE is_published = true
  `
  return rows as unknown as { slug: string; updated_at: string }[]
}

// ─── Products ────────────────────────────────────────────────────────────────

export async function getLatestProducts(limit = 12): Promise<Product[]> {
  const rows = await sql`
    SELECT * FROM g_products
    WHERE is_published = true AND in_stock = true
    ORDER BY updated_at DESC
    LIMIT ${limit}
  `
  return rows as unknown as Product[]
}

export async function getProductBySlug(slug: string): Promise<Product | null> {
  const rows = await sql`
    SELECT * FROM g_products
    WHERE slug = ${slug} AND is_published = true
    LIMIT 1
  `
  return (rows[0] ?? null) as Product | null
}

export async function getProductsByCategoryId(categoryId: number, limit = 9999, offset = 0): Promise<Product[]> {
  const rows = await sql`
    SELECT * FROM g_products
    WHERE category_id = ${categoryId} AND is_published = true
    ORDER BY in_stock DESC, updated_at DESC
    LIMIT ${limit} OFFSET ${offset}
  `
  return rows as unknown as Product[]
}

export async function getProductSummaryByCategoryId(categoryId: number): Promise<{ brand: string; price_rub: number | null; in_stock: boolean }[]> {
  const rows = await sql`
    SELECT brand, price_rub, in_stock
    FROM g_products
    WHERE category_id = ${categoryId} AND is_published = true
    ORDER BY in_stock DESC, updated_at DESC
  `
  return rows as unknown as { brand: string; price_rub: number | null; in_stock: boolean }[]
}

// Products in the same price range (±10%), ordered by: same category → same brand → price closeness
export async function getSamePriceProducts(
  price: number,
  categoryId: number,
  brand: string,
  excludeId: number,
  limit = 8,
): Promise<Product[]> {
  const lo = Math.round(price * 0.9)
  const hi = Math.round(price * 1.1)
  const rows = await sql`
    SELECT *,
      (category_id = ${categoryId})::int AS same_cat,
      (brand = ${brand})::int        AS same_brand,
      ABS(price_rub - ${price})      AS price_diff
    FROM g_products
    WHERE is_published = true
      AND id != ${excludeId}
      AND price_rub IS NOT NULL
      AND price_rub BETWEEN ${lo} AND ${hi}
    ORDER BY same_cat DESC, same_brand DESC, price_diff ASC
    LIMIT ${limit}
  `
  return rows as unknown as Product[]
}

// Complementary category rules for "Обычно заказывают вместе"
const COMPLEMENTARY: Record<string, string[]> = {
  smartphones: ['watches', 'headphones', 'tablets', 'accessories'],
  tablets:     ['headphones', 'watches', 'accessories', 'laptops'],
  laptops:     ['headphones', 'tablets', 'accessories'],
  watches:     ['smartphones', 'tablets'],
  headphones:  ['smartphones', 'tablets', 'laptops'],
  accessories: ['smartphones', 'tablets', 'laptops'],
  gaming:      ['gaming', 'headphones'],
  appliances:  ['appliances'],
  lego:        ['lego'],
}

export async function getBoughtTogetherProducts(
  currentId: number,
  categorySlug: string,
  brand: string,
  limit = 4,
): Promise<Product[]> {
  const slugs = COMPLEMENTARY[categorySlug] ?? []
  if (!slugs.length) return []
  const rows = await sql`
    SELECT p.*,
      (p.brand = ${brand})::int AS same_brand
    FROM g_products p
    JOIN g_categories c ON c.id = p.category_id
    WHERE c.slug = ANY(${slugs})
      AND p.is_published = true
      AND p.id != ${currentId}
      AND p.in_stock = true
    ORDER BY same_brand DESC, p.price_rub ASC NULLS LAST
    LIMIT ${limit}
  `
  return rows as unknown as Product[]
}

export async function getAllPublishedProductsForBrand(): Promise<Product[]> {
  const rows = await sql`
    SELECT * FROM g_products WHERE is_published = true
  `
  return rows as unknown as Product[]
}

export async function getAllPublishedProductSlugs(): Promise<{ slug: string; brand: string; updated_at: string }[]> {
  const rows = await sql`
    SELECT slug, brand, updated_at FROM g_products WHERE is_published = true
  `
  return rows as unknown as { slug: string; brand: string; updated_at: string }[]
}

// ─── Price history (cron) ────────────────────────────────────────────────────

export async function getProductsForPriceCheck(limit = 50): Promise<{
  id: number
  slug: string
  biggeek_url: string
  price_rub: number | null
  in_stock: boolean
}[]> {
  const rows = await sql`
    SELECT id, slug, biggeek_url, price_rub, in_stock
    FROM g_products
    ORDER BY last_checked_at ASC NULLS FIRST
    LIMIT ${limit}
  `
  return rows as unknown as {
    id: number
    slug: string
    biggeek_url: string
    price_rub: number | null
    in_stock: boolean
  }[]
}

export async function insertPriceHistory(productId: number, priceRub: number, inStock: boolean): Promise<void> {
  await sql`
    INSERT INTO g_price_history (product_id, price_rub, in_stock)
    VALUES (${productId}, ${priceRub}, ${inStock})
  `
}

export async function updateProductPriceState(
  id: number,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  patch: Record<string, any>
): Promise<void> {
  await sql`
    UPDATE g_products SET ${sql(patch)} WHERE id = ${id}
  `
}
