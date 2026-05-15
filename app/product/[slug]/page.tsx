import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { getProductBySlug, getCategoryById, getSamePriceProducts, getBoughtTogetherProducts } from '@/lib/db'
import { Breadcrumbs } from '@/components/Breadcrumbs'
import { ProductCard } from '@/components/ProductCard'
import { formatPrice, buildAffiliateLink } from '@/lib/utils'
import { splitSpecs } from '@/lib/specs'

export const revalidate = 3600

interface Props {
  params: Promise<{ slug: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const product = await getProductBySlug(slug)
  if (!product) return {}
  return {
    title: product.meta_title ?? `${product.name} — характеристики и цена`,
    description:
      product.meta_description ??
      `${product.brand} ${product.name} — описание, характеристики и актуальная цена. Покупка через biggeek.ru.`,
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
          <div className="aspect-square bg-gray-50 rounded-2xl overflow-hidden relative mb-3">
            {product.image_urls[0] ? (
              <Image
                src={product.image_urls[0]}
                alt={product.name}
                fill
                sizes="(max-width: 768px) 100vw, 50vw"
                className="object-contain p-6"
                itemProp="image"
                priority
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-gray-300 text-sm">
                Нет фото
              </div>
            )}
          </div>
          {product.image_urls.length > 1 && (
            <div className="grid grid-cols-5 gap-2">
              {product.image_urls.slice(1, 6).map((url, i) => (
                <div key={i} className="aspect-square bg-gray-50 rounded-lg overflow-hidden relative">
                  <Image
                    src={url}
                    alt={`${product.name} — фото ${i + 2}`}
                    fill
                    sizes="20vw"
                    className="object-contain p-2"
                  />
                </div>
              ))}
            </div>
          )}
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

            <p className="text-xs text-gray-400 mt-3 leading-relaxed">
              Партнёрская ссылка. Цена и наличие могут отличаться от указанных — актуальные данные смотрите на сайте продавца.
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
