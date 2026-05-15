'use server'

import { getProductsByCategoryId } from '@/lib/db'

export async function loadMoreProducts(categoryId: number, offset: number) {
  return getProductsByCategoryId(categoryId, 36, offset)
}
