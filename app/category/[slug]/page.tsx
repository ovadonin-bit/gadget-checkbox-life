import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { getCategoryBySlug, getProductsByCategoryId, getProductSummaryByCategoryId } from '@/lib/db'
import { CategoryProductGrid } from '@/components/CategoryProductGrid'
import { Breadcrumbs } from '@/components/Breadcrumbs'
import { formatPriceNumber } from '@/lib/utils'

const PAGE_SIZE = 36

export const revalidate = 3600

interface Props {
  params: Promise<{ slug: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const category = await getCategoryBySlug(slug)
  if (!category) return {}
  return {
    title: category.meta_title ?? `${category.name} — Купить. Самая низкая цена в России.`,
    description: category.meta_description ?? `${category.name} — честное описание, полные характеристики и актуальные цены. Сравни с альтернативами и купи выгодно.`,
    alternates: { canonical: `https://gadget.checkbox.life/category/${category.slug}` },
  }
}

export default async function CategoryPage({ params }: Props) {
  const { slug } = await params
  const category = await getCategoryBySlug(slug)
  if (!category) notFound()

  const [summary, initialProducts] = await Promise.all([
    getProductSummaryByCategoryId(category.id),
    getProductsByCategoryId(category.id, PAGE_SIZE, 0),
  ])

  const totalCount = summary.length
  const inStock = summary.filter((p) => p.in_stock && p.price_rub != null)
  const prices = inStock.map((p) => p.price_rub!).filter((n) => n > 0)
  const lowPrice = prices.length ? Math.min(...prices) : null
  const highPrice = prices.length ? Math.max(...prices) : null

  const brandCounts = new Map<string, number>()
  for (const p of summary) {
    brandCounts.set(p.brand, (brandCounts.get(p.brand) ?? 0) + 1)
  }
  const brands = [...brandCounts.entries()].sort((a, b) => b[1] - a[1])

  return (
    <main
      className="max-w-6xl mx-auto px-4 py-6"
      itemScope
      itemType="https://schema.org/CollectionPage"
    >
      <Breadcrumbs
        items={[
          { name: 'Главная', href: '/' },
          { name: category.name, href: `/category/${category.slug}` },
        ]}
      />

      <h1 className="text-2xl sm:text-3xl font-semibold text-gray-900 tracking-tight mb-2" itemProp="name">
        {category.name}
      </h1>
      {category.description_html && (
        <div
          className="product-description text-sm text-gray-600 mb-4 max-w-3xl"
          dangerouslySetInnerHTML={{ __html: category.description_html }}
        />
      )}

      <div className="text-xs text-gray-500 mb-6">
        Товаров в каталоге: {totalCount}
        {prices.length > 0 && lowPrice != null && highPrice != null && (
          <> · Цены от {formatPriceNumber(lowPrice)} до {formatPriceNumber(highPrice)} ₽</>
        )}
      </div>

      {prices.length > 0 && lowPrice != null && highPrice != null && (
        <div
          itemProp="mainEntity"
          itemScope
          itemType="https://schema.org/AggregateOffer"
          className="hidden"
        >
          <meta itemProp="priceCurrency" content="RUB" />
          <meta itemProp="lowPrice" content={String(lowPrice)} />
          <meta itemProp="highPrice" content={String(highPrice)} />
          <meta itemProp="offerCount" content={String(inStock.length)} />
        </div>
      )}

      {brands.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Бренды</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {brands.map(([brand]) => (
              <Link
                key={brand}
                href={`/brand/${brand.toLowerCase().replace(/\s+/g, '-')}`}
                className="block rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all bg-white p-4 text-center"
              >
                <div className="text-sm font-medium text-gray-900">{brand}</div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {totalCount === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-8 text-center text-sm text-gray-500">
          Товары в этой категории появятся после первого парсинга. Возвращайтесь позже.
        </div>
      ) : (
        <CategoryProductGrid
          initialProducts={initialProducts}
          totalCount={totalCount}
          categoryId={category.id}
        />
      )}
    </main>
  )
}
