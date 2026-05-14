export function formatPrice(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatPriceNumber(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(value)
}

export function slugifyBrand(brand: string): string {
  return brand
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
}

/**
 * Превращает ссылку biggeek.ru в Admitad-deeplink.
 * Формат заполнится после получения оффера в Admitad.
 */
export function buildAffiliateLink(biggeekUrl: string): string {
  const campaignId = process.env.ADMITAD_CAMPAIGN_ID
  const affiliateId = process.env.NEXT_PUBLIC_ADMITAD_AFFILIATE_ID
  const subid = process.env.NEXT_PUBLIC_ADMITAD_SUBID ?? 'gadget'

  if (!campaignId || !affiliateId) {
    return biggeekUrl
  }

  // Admitad standard deeplink format:
  // https://ad.admitad.com/g/{affiliateId}/?ulp={encoded biggeek url}&subid={subid}
  const ulp = encodeURIComponent(biggeekUrl)
  return `https://ad.admitad.com/g/${affiliateId}/?ulp=${ulp}&subid=${subid}`
}
