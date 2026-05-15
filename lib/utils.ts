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

const HISTORE_DEEPLINK = 'https://wpmsx.com/g/hwysxaae1b7ad04f0a593a4ea8cf25/?erid=2bL9aMPo2e49hMef4piUAotQ6a'
const BEELINE_DEEPLINK = 'https://rcpsj.com/g/exxsgtkm6c7ad04f0a59dbadac95b8/?erid=2bL9aMPo2e49hMef4phUdXKkvx'
const ONECLICK_DEEPLINK = 'https://dbnua.com/g/3r14duvwf07ad04f0a599ac4fee4f4/?erid=2bL9aMPo2e49hMef4rqytJL1Um'

export function buildHistoreDeeplink(productUrl: string): string {
  return `${HISTORE_DEEPLINK}&ulp=${encodeURIComponent(productUrl)}`
}

export function buildBeelineDeeplink(productUrl: string): string {
  return `${BEELINE_DEEPLINK}&ulp=${encodeURIComponent(productUrl)}`
}

export function buildOneclickDeeplink(productUrl: string): string {
  return `${ONECLICK_DEEPLINK}&ulp=${encodeURIComponent(productUrl)}`
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
