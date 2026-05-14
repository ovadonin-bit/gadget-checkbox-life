/**
 * Парсер карточки biggeek.ru — только то, что нужно для refresh-prices:
 * JSON-LD Product → price/availability + старая цена из <span class="old-price">.
 * Логика 1-в-1 с scripts/lib_biggeek.py.
 */

const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

export type FetchStatus = 'ok' | 'not_found' | 'error'

export type ProductState = {
  price: number | null
  oldPrice: number | null
  inStock: boolean
}

export type FetchResult =
  | { status: 'ok'; state: ProductState }
  | { status: 'not_found'; state: null }
  | { status: 'error'; state: null }

function extractJsonLdProduct(html: string): Record<string, unknown> | null {
  const re = /<script type="application\/ld\+json">([\s\S]+?)<\/script>/g
  let m: RegExpExecArray | null
  while ((m = re.exec(html)) !== null) {
    try {
      const data = JSON.parse(m[1].trim())
      if (data && typeof data === 'object' && data['@type'] === 'Product') return data
    } catch {
      // ignore malformed blocks
    }
  }
  return null
}

function parseOldPrice(html: string): number | null {
  const m = html.match(/<span class="old-price">\s*([\d\s]+?)\s*<\/span>/)
  if (!m) return null
  const digits = m[1].replace(/\D/g, '')
  return digits ? Number(digits) : null
}

export async function fetchProductState(url: string): Promise<FetchResult> {
  let res: Response
  try {
    res = await fetch(url, {
      headers: { 'User-Agent': UA, 'Accept-Language': 'ru,en;q=0.9' },
      cache: 'no-store',
      signal: AbortSignal.timeout(15_000),
    })
  } catch {
    return { status: 'error', state: null }
  }
  if (res.status === 404) return { status: 'not_found', state: null }
  if (!res.ok) return { status: 'error', state: null }

  const html = await res.text()
  const jsonld = extractJsonLdProduct(html)
  if (!jsonld) return { status: 'error', state: null }

  let offer = (jsonld as { offers?: unknown }).offers
  if (Array.isArray(offer)) offer = offer[0]
  const o = (offer ?? {}) as { price?: unknown; availability?: unknown }

  const priceNum = Number(o.price)
  const price = Number.isFinite(priceNum) ? priceNum : null
  const availability = String(o.availability ?? '')
  const inStock = availability.endsWith('InStock') || availability.endsWith('PreOrder')

  return {
    status: 'ok',
    state: { price, oldPrice: parseOldPrice(html), inStock },
  }
}
