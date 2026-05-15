import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { getProductBySlug, getCategoryById, getSamePriceProducts, getBoughtTogetherProducts } from '@/lib/db'
import { Breadcrumbs } from '@/components/Breadcrumbs'
import { ProductCard } from '@/components/ProductCard'
import { ImageGallery } from '@/components/ImageGallery'
import { formatPrice, formatPriceNumber, buildAffiliateLink, buildHistoreDeeplink, buildBeelineDeeplink, buildOneclickDeeplink } from '@/lib/utils'
import { splitSpecs } from '@/lib/specs'

export const revalidate = 3600

const KEY_SPECS: Array<[string, string]> = [
  ['Объем встроенной памяти', 'памяти'],
  ['Объем оперативной памяти', 'RAM'],
  ['Процессор', 'процессор'],
  ['Экран', 'экран'],
  ['Ёмкость аккумулятора', 'батарея'],
  ['Основная камера', 'камера'],
  ['Размер корпуса', 'размер'],
  ['Время работы', 'автономность'],
]

function buildProductMeta(brand: string, name: string, price: number | null, specs: Record<string, string> | null) {
  const priceStr = price != null ? ` ${formatPriceNumber(price)} ₽` : ''
  const title = `${name}${priceStr} — Где купить? Цены. Обзор, характеристики.`

  const keySpecParts: string[] = []
  if (specs) {
    for (const [key, label] of KEY_SPECS) {
      if (specs[key]) {
        keySpecParts.push(`${specs[key]} ${label}`)
        if (keySpecParts.length >= 2) break
      }
    }
  }
  const specsStr = keySpecParts.length > 0 ? ` ${keySpecParts.join(', ')}.` : ''
  const priceDescStr = price != null ? ` за ${formatPriceNumber(price)} ₽` : ''
  const description = `Купить ${brand} ${name}${priceDescStr} — характеристики, фото, описание.${specsStr} Доставка по России.`

  return { title, description }
}

interface Props {
  params: Promise<{ slug: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const product = await getProductBySlug(slug)
  if (!product) return {}
  const { title: autoTitle, description: autoDescription } = buildProductMeta(
    product.brand,
    product.name,
    product.price_rub,
    product.specs as Record<string, string> | null,
  )
  return {
    title: product.meta_title ?? autoTitle,
    description: product.meta_description ?? autoDescription,
    alternates: { canonical: `https://gadget.checkbox.life/product/${product.slug}` },
    openGraph: {
      title: product.name,
      images: product.image_urls.slice(0, 1),
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title: product.name,
      images: product.image_urls.slice(0, 1),
    },
  }
}

export default async function ProductPage({ params }: Props) {
  const { slug } = await params
  const product = await getProductBySlug(slug)
  if (!product) notFound()

  const category = await getCategoryById(product.category_id)
  const [samePrice, boughtTogether] = await Promise.all([
    product.price_rub != null
      ? getSamePriceProducts(product.price_rub, product.category_id, product.brand, product.id, 8)
      : Promise.resolve([]),
    getBoughtTogetherProducts(product.id, category?.slug ?? '', product.brand, 4),
  ])

  const availability = product.in_stock
    ? 'https://schema.org/InStock'
    : 'https://schema.org/OutOfStock'
  const productUrl = `https://gadget.checkbox.life/product/${product.slug}`
  const affiliateLink = buildAffiliateLink(product.biggeek_url)

  const priceValidUntil = new Date()
  priceValidUntil.setDate(priceValidUntil.getDate() + 30)
  const priceValidUntilStr = priceValidUntil.toISOString().slice(0, 10)

  const breadcrumbs = [
    { name: 'Главная', href: '/' },
    ...(category ? [{ name: category.name, href: `/category/${category.slug}` }] : []),
    { name: product.name, href: `/product/${product.slug}` },
  ]

  const { primary: primarySpecs, secondary: secondarySpecs } = splitSpecs(product.specs)

  return (
    <main className="max-w-6xl mx-auto px-4 py-6">
      <Breadcrumbs items={breadcrumbs} />

      <article
        itemScope
        itemType="https://schema.org/Product"
        className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12"
      >
        {/* Галерея */}
        <div>
          <ImageGallery images={product.image_urls} productName={product.name} />
          <p className="text-xs text-gray-400 mt-2">
            Фото:{' '}
            <a
              href={product.biggeek_url}
              rel="nofollow noopener"
              target="_blank"
              className="underline hover:text-gray-700"
            >
              biggeek.ru
            </a>
          </p>
        </div>

        {/* Информация */}
        <div>
          <div className="text-sm text-gray-500 mb-1" itemProp="brand" itemScope itemType="https://schema.org/Brand">
            <span itemProp="name">{product.brand}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-gray-900 tracking-tight mb-3" itemProp="name">
            {product.name}
          </h1>

          {product.sku && (
            <div className="text-xs text-gray-400 mb-4">
              Артикул: <span itemProp="sku">{product.sku}</span>
            </div>
          )}

          {/* Offer */}
          <div
            itemProp="offers"
            itemScope
            itemType="https://schema.org/Offer"
            className="rounded-2xl border border-gray-200 bg-white p-5 mb-4"
          >
            <link itemProp="url" href={productUrl} />
            <meta itemProp="priceCurrency" content="RUB" />
            <link itemProp="availability" href={availability} />
            <meta itemProp="priceValidUntil" content={priceValidUntilStr} />
            <link itemProp="itemCondition" href="https://schema.org/NewCondition" />

            <div className="flex items-baseline gap-3 mb-4">
              <div className="text-3xl font-semibold text-gray-900">
                <meta itemProp="price" content={product.price_rub != null ? String(product.price_rub) : '0'} />
                {formatPrice(product.price_rub)}
              </div>
              {product.old_price_rub != null && product.old_price_rub > (product.price_rub ?? 0) && (
                <span className="text-base text-gray-400 line-through">
                  {formatPrice(product.old_price_rub)}
                </span>
              )}
            </div>

            <div className="text-xs mb-4">
              {product.in_stock ? (
                <span className="text-green-700 font-medium">В наличии</span>
              ) : (
                <span className="text-amber-600 font-medium">Нет в наличии</span>
              )}
            </div>

            <a
              href={affiliateLink}
              target="_blank"
              rel="nofollow noopener sponsored"
              className="block w-full text-center bg-gray-900 hover:bg-black text-white font-medium text-sm py-3 rounded-xl transition-colors"
            >
              Купить на biggeek.ru
            </a>

            {(product.histore_url || product.beeline_url || product.oneclick_url) && (
              <div className="flex flex-col gap-2 mt-2">
                {product.histore_url && (
                  <a
                    href={buildHistoreDeeplink(product.histore_url)}
                    target="_blank"
                    rel="nofollow noopener sponsored"
                    className="block w-full text-center bg-white hover:bg-gray-50 text-gray-900 font-medium text-sm py-3 rounded-xl border border-gray-200 transition-colors"
                  >
                    Купить на Hi Store
                  </a>
                )}
                {product.beeline_url && (
                  <a
                    href={buildBeelineDeeplink(product.beeline_url)}
                    target="_blank"
                    rel="nofollow noopener sponsored"
                    className="block w-full text-center bg-white hover:bg-gray-50 text-gray-900 font-medium text-sm py-3 rounded-xl border border-gray-200 transition-colors"
                  >
                    Купить на Билайн.ру
                  </a>
                )}
                {product.oneclick_url && (
                  <a
                    href={buildOneclickDeeplink(product.oneclick_url)}
                    target="_blank"
                    rel="nofollow noopener sponsored"
                    className="block w-full text-center bg-white hover:bg-gray-50 text-gray-900 font-medium text-sm py-3 rounded-xl border border-gray-200 transition-colors"
                  >
                    Купить на 1click.ru
                  </a>
                )}
              </div>
            )}

            <p className="text-xs text-gray-400 mt-3 leading-relaxed">
              Партнёрские ссылки. Цена и наличие могут отличаться от указанных — актуальные данные смотрите на сайте продавца.
            </p>

            <div itemProp="seller" itemScope itemType="https://schema.org/Organization" className="hidden">
              <meta itemProp="name" content="biggeek.ru" />
              <link itemProp="url" href="https://biggeek.ru" />
            </div>
          </div>

          {primarySpecs.length > 0 && (
            <div className="rounded-2xl border border-gray-200 bg-white p-5 mb-4">
              <h2 className="text-sm font-semibold text-gray-900 mb-3">Ключевые характеристики</h2>
              <dl className="grid grid-cols-1 gap-y-1.5 text-xs">
                {primarySpecs.map(([k, v]) => (
                  <div key={k} className="grid grid-cols-2 gap-2">
                    <dt className="text-gray-500">{k}</dt>
                    <dd className="text-gray-900">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>

        {product.description_html && (
          <div className="md:col-span-2 rounded-2xl border border-gray-200 bg-white p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Описание</h2>
            <div
              className="product-description"
              itemProp="description"
              dangerouslySetInnerHTML={{ __html: product.description_html }}
            />
            <p className="text-xs text-gray-400 mt-4 pt-4 border-t border-gray-100">
              Характеристики приведены на основе данных с сайта{' '}
              <a href={product.biggeek_url} rel="nofollow noopener" target="_blank" className="underline hover:text-gray-700">
                biggeek.ru
              </a>.
            </p>
          </div>
        )}

        {secondarySpecs.length > 0 && (
          <div className="md:col-span-2 rounded-2xl border border-gray-200 bg-white p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Все характеристики</h2>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1.5 text-xs">
              {secondarySpecs.map(([k, v]) => (
                <div key={k} className="grid grid-cols-2 gap-2">
                  <dt className="text-gray-500">{k}</dt>
                  <dd className="text-gray-900">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </article>

      {boughtTogether.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Обычно заказывают вместе</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {boughtTogether.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}

      {samePrice.length > 0 && (
        <section className="mb-12">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">За ту же цену</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {samePrice.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}

      {category && (
        <div className="text-xs text-gray-500">
          <Link href={`/category/${category.slug}`} className="hover:text-gray-900">
            ← Все товары в категории «{category.name}»
          </Link>
        </div>
      )}
    </main>
  )
}
