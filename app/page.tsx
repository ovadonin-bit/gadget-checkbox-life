import Link from 'next/link'
import { getPublishedRootCategories, getLatestProducts } from '@/lib/db'
import { ProductCard } from '@/components/ProductCard'

export const revalidate = 3600

export default async function HomePage() {
  const [categories, products] = await Promise.all([
    getPublishedRootCategories(),
    getLatestProducts(12),
  ])

  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      <section className="mb-12">
        <h1 className="text-3xl sm:text-4xl font-semibold text-gray-900 tracking-tight mb-3">
          Каталог электроники
        </h1>
        <p className="text-base text-gray-600 max-w-2xl">
          Смартфоны, ноутбуки, планшеты и аксессуары с актуальными ценами.
          Покупка через партнёра <a href="https://biggeek.ru" rel="nofollow noopener" className="text-gray-900 underline">biggeek.ru</a>.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Категории</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {categories.map((c) => (
            <Link
              key={c.slug}
              href={`/category/${c.slug}`}
              className="block rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all bg-white p-4 text-center"
            >
              <div className="text-sm font-medium text-gray-900">{c.name}</div>
            </Link>
          ))}
        </div>
      </section>

      {products.length > 0 && (
        <section className="mb-12">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Новинки</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}
    </main>
  )
}
