'use client'

import { useState, useTransition } from 'react'
import { ProductCard } from '@/components/ProductCard'
import type { Product } from '@/types/db'

interface Props {
  initialProducts: Product[]
  totalCount: number
  loader: (offset: number) => Promise<Product[]>
}

export function ProductGrid({ initialProducts, totalCount, loader }: Props) {
  const [products, setProducts] = useState(initialProducts)
  const [isPending, startTransition] = useTransition()

  const hasMore = products.length < totalCount

  function handleLoadMore() {
    startTransition(async () => {
      const more = await loader(products.length)
      setProducts((prev) => [...prev, ...more])
    })
  }

  return (
    <>
      <div
        itemScope
        itemType="https://schema.org/ItemList"
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3"
      >
        <meta itemProp="numberOfItems" content={String(totalCount)} />
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

      {hasMore && (
        <div className="mt-8 flex justify-center">
          <button
            onClick={handleLoadMore}
            disabled={isPending}
            className="px-6 py-2.5 rounded-xl border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {isPending ? 'Загрузка…' : `Показать ещё · ${totalCount - products.length}`}
          </button>
        </div>
      )}
    </>
  )
}
