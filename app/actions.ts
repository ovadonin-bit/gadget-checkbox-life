'use server'

import { getProductsByCategoryId, getProductsByBrand } from '@/lib/db'

export async function loadMoreProducts(categoryId: number, offset: number) {
  return getProductsByCategoryId(categoryId, 36, offset)
}

export async function loadMoreProductsByBrand(brand: string, offset: number) {
  return getProductsByBrand(brand, 36, offset)
}
