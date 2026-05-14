import type { MetadataRoute } from 'next'
import { getAllPublishedCategorySlugs, getAllPublishedProductSlugs } from '@/lib/db'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://gadget.checkbox.life'

  const [categories, products] = await Promise.all([
    getAllPublishedCategorySlugs(),
    getAllPublishedProductSlugs(),
  ])

  const categoryUrls: MetadataRoute.Sitemap = categories.map((c) => ({
    url: `${baseUrl}/category/${c.slug}`,
    lastModified: new Date(c.updated_at),
    changeFrequency: 'daily',
    priority: 0.8,
  }))

  const productUrls: MetadataRoute.Sitemap = products.map((p) => ({
    url: `${baseUrl}/product/${p.slug}`,
    lastModified: new Date(p.updated_at),
    changeFrequency: 'daily',
    priority: 0.7,
  }))

  const brands = [...new Set(products.map((p) => p.brand.toLowerCase().replace(/\s+/g, '-')))]
  const brandUrls: MetadataRoute.Sitemap = brands.map((b) => ({
    url: `${baseUrl}/brand/${b}`,
    changeFrequency: 'weekly',
    priority: 0.6,
  }))

  return [
    { url: baseUrl, changeFrequency: 'daily', priority: 1.0 },
    ...categoryUrls,
    ...brandUrls,
    ...productUrls,
  ]
}
