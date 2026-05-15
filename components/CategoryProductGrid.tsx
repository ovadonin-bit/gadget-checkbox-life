'use client'

import { ProductGrid } from '@/components/ProductGrid'
import { loadMoreProducts } from '@/app/actions'
import type { Product } from '@/types/db'

interface Props {
  initialProducts: Product[]
  totalCount: number
  categoryId: number
}

export function CategoryProductGrid({ initialProducts, totalCount, categoryId }: Props) {
  return (
    <ProductGrid
      initialProducts={initialProducts}
      totalCount={totalCount}
      loader={(offset) => loadMoreProducts(categoryId, offset)}
    />
  )
}
