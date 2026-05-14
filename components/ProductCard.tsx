import Link from 'next/link'
import Image from 'next/image'
import type { Product } from '@/types/db'
import { formatPrice } from '@/lib/utils'

/**
 * Карточка товара в листинге. Использует microdata schema.org/Product
 * чтобы быть валидной точкой ItemList на странице категории.
 */
export function ProductCard({ product }: { product: Product }) {
  const firstImage = product.image_urls[0]
  const availability = product.in_stock
    ? 'https://schema.org/InStock'
    : 'https://schema.org/OutOfStock'
  const productUrl = `/product/${product.slug}`

  return (
    <Link
      href={productUrl}
      itemScope
      itemType="https://schema.org/Product"
      className="group block rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all bg-white overflow-hidden"
    >
      <div className="aspect-square bg-gray-50 relative">
        {firstImage ? (
          <Image
            src={firstImage}
            alt={product.name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-contain p-4 group-hover:scale-105 transition-transform"
            itemProp="image"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-gray-300 text-xs">
            Нет фото
          </div>
        )}
      </div>
      <div className="p-3">
        <div className="text-xs text-gray-400 mb-0.5" itemProp="brand">
          {product.brand}
        </div>
        <div className="text-sm font-medium text-gray-900 line-clamp-2 min-h-[2.5rem]" itemProp="name">
          {product.name}
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <div
            className="text-base font-semibold text-gray-900"
            itemProp="offers"
            itemScope
            itemType="https://schema.org/Offer"
          >
            <meta itemProp="priceCurrency" content="RUB" />
            <meta itemProp="price" content={product.price_rub != null ? String(product.price_rub) : '0'} />
            <link itemProp="availability" href={availability} />
            <link itemProp="url" href={productUrl} />
            {formatPrice(product.price_rub)}
          </div>
          {product.old_price_rub != null && product.old_price_rub > (product.price_rub ?? 0) && (
            <span className="text-xs text-gray-400 line-through">
              {formatPrice(product.old_price_rub)}
            </span>
          )}
        </div>
        {!product.in_stock && (
          <div className="mt-1 text-xs text-amber-600">Нет в наличии</div>
        )}
      </div>
    </Link>
  )
}
