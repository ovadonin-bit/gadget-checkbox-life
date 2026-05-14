import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { getAllPublishedProductsForBrand } from '@/lib/db'
import { ProductCard } from '@/components/ProductCard'
import { Breadcrumbs } from '@/components/Breadcrumbs'
import { formatPriceNumber } from '@/lib/utils'

export const revalidate = 3600

interface Props {
  params: Promise<{ slug: string }>
}

function brandFromSlug(slug: string): string {
  return slug
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const brand = brandFromSlug(slug)
  return {
    title: `${brand} — все товары`,
    description: `Каталог товаров ${brand}: смартфоны, ноутбуки, аксессуары с актуальными ценами через biggeek.ru.`,
    alternates: { canonical: `https://gadget.checkbox.life/brand/${slug}` },
  }
}

export default async function BrandPage({ params }: Props) {
  const { slug } = await params

  const allProducts = await getAllPublishedProductsForBrand()
  const products = allProducts.filter(
    (p) => p.brand.toLowerCase().replace(/\s+/g, '-') === slug
  )

  if (products.length === 0) notFound()

  const brand = products[0].brand
  const inStock = products.filter((p) => p.in_stock && p.price_rub != null)
  const prices = inStock.map((p) => p.price_rub!).filter((n) => n > 0)
  const lowPrice = prices.length ? Math.min(...prices) : null
  const highPrice = prices.length ? Math.max(...prices) : null

  return (
    <main className="max-w-6xl mx-auto px-4 py-6">
      <Breadcrumbs
        items={[
          { name: 'Главная', href: '/' },
          { name: brand, href: `/brand/${slug}` },
        ]}
      />

      <h1 className="text-2xl sm:text-3xl font-semibold text-gray-900 tracking-tight mb-2">{brand}</h1>
      <div className="text-xs text-gray-500 mb-6">
        Товаров: {products.length}
        {prices.length > 0 && lowPrice != null && highPrice != null && (
          <> · Цены от {formatPriceNumber(lowPrice)} до {formatPriceNumber(highPrice)} ₽</>
        )}
      </div>

      <div
        itemScope
        itemType="https://schema.org/ItemList"
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3"
      >
        <meta itemProp="numberOfItems" content={String(products.length)} />
        {products.map((p, i) => (
          <div
            key={p.id}
            itemProp="itemListElement"
            itemScope
            itemType="https://schema.org/ListItem"
          >
            <meta itemProp="position" content={String(i + 1)} />
            <ProductCard product={p} />
          </div>
        ))}
      </div>
    </main>
  )
}
