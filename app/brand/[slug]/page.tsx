import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { getProductsByBrand, getProductSummaryByBrand, getPublishedRootCategories } from '@/lib/db'
import { ProductGrid } from '@/components/ProductGrid'
import { Breadcrumbs } from '@/components/Breadcrumbs'
import { formatPriceNumber, slugifyBrand } from '@/lib/utils'
import { loadMoreProductsByBrand } from '@/app/actions'

export const revalidate = 3600

const PAGE_SIZE = 36

interface Props {
  params: Promise<{ slug: string }>
}

function brandFromSlug(slug: string): string {
  return slug
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

async function getPrimaryCategory(brand: string): Promise<string | null> {
  const [summary, categories] = await Promise.all([
    getProductSummaryByBrand(brand),
    getPublishedRootCategories(),
  ])
  if (!summary.length) return null
  const counts = new Map<number, number>()
  for (const p of summary) counts.set(p.category_id, (counts.get(p.category_id) ?? 0) + 1)
  const topCatId = [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0]
  const cat = categories.find((c) => c.id === topCatId)
  if (!cat?.meta_title) return null
  return cat.meta_title.split(' — ')[0]
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const brand = brandFromSlug(slug)
  const primaryCategory = await getPrimaryCategory(brand)
  const titlePrefix = primaryCategory ?? brand
  return {
    title: `${titlePrefix} ${brand} — Купить. Самая низкая цена в России.`,
    description: `${titlePrefix} ${brand} — честное описание, полные характеристики и актуальные цены. Сравни с альтернативами и купи выгодно.`,
    alternates: { canonical: `https://gadget.checkbox.life/brand/${slug}` },
  }
}

export default async function BrandPage({ params }: Props) {
  const { slug } = await params
  const brand = brandFromSlug(slug)

  const [summary, initialProducts] = await Promise.all([
    getProductSummaryByBrand(brand),
    getProductsByBrand(brand, PAGE_SIZE, 0),
  ])

  if (!summary.length) notFound()

  const totalCount = summary.length
  const inStock = summary.filter((p) => p.in_stock && p.price_rub != null)
  const prices = inStock.map((p) => p.price_rub!).filter((n) => n > 0)
  const lowPrice = prices.length ? Math.min(...prices) : null
  const highPrice = prices.length ? Math.max(...prices) : null

  const loader = loadMoreProductsByBrand.bind(null, brand)

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
        Товаров: {totalCount}
        {prices.length > 0 && lowPrice != null && highPrice != null && (
          <> · Цены от {formatPriceNumber(lowPrice)} до {formatPriceNumber(highPrice)} ₽</>
        )}
      </div>

      <ProductGrid
        initialProducts={initialProducts}
        totalCount={totalCount}
        loader={loader}
      />
    </main>
  )
}
