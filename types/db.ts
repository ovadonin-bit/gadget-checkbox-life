export type Availability =
  | 'https://schema.org/InStock'
  | 'https://schema.org/OutOfStock'
  | 'https://schema.org/PreOrder'

export interface Category {
  id: number
  slug: string
  name: string
  parent_id: number | null
  description_html: string | null
  meta_title: string | null
  meta_description: string | null
  sort_order: number
  is_published: boolean
}

export interface Product {
  id: number
  slug: string
  category_id: number
  brand: string
  name: string
  biggeek_url: string
  biggeek_product_id: string | null
  sku: string | null
  price_rub: number | null
  old_price_rub: number | null
  in_stock: boolean
  description_html: string | null
  specs: Record<string, string> | null
  image_urls: string[]
  meta_title: string | null
  meta_description: string | null
  updated_at: string
  is_published: boolean
  histore_url: string | null
  beeline_url: string | null
}

export interface PriceHistoryRow {
  product_id: number
  price_rub: number
  in_stock: boolean
  captured_at: string
}
