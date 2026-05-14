import { getProductsForPriceCheck, insertPriceHistory, updateProductPriceState } from '@/lib/db'
import { fetchProductState } from '@/lib/biggeek-parser'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'
export const maxDuration = 60

const BATCH_SIZE = 50
const REQUEST_DELAY_MS = 300

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

export async function GET(req: Request) {
  const auth = req.headers.get('authorization')
  if (auth !== `Bearer ${process.env.CRON_SECRET}`) {
    return new Response('Unauthorized', { status: 401 })
  }

  const products = await getProductsForPriceCheck(BATCH_SIZE)

  const stats = {
    batch: products.length,
    checked: 0,
    priceChanged: 0,
    stockChanged: 0,
    notFound: 0,
    errors: 0,
  }
  const now = new Date().toISOString()

  for (const p of products) {
    if (!p.biggeek_url) continue

    const result = await fetchProductState(p.biggeek_url)
    stats.checked++

    const patch: Record<string, unknown> = {
      last_checked_at: now,
      source_status: result.status,
    }

    if (result.status === 'ok') {
      patch.last_seen_at = now
      patch.price_rub = result.state.price
      patch.old_price_rub = result.state.oldPrice
      patch.in_stock = result.state.inStock

      const priceChanged = result.state.price !== p.price_rub
      const stockChanged = result.state.inStock !== p.in_stock
      if ((priceChanged || stockChanged) && result.state.price !== null) {
        await insertPriceHistory(p.id, result.state.price, result.state.inStock)
        if (priceChanged) stats.priceChanged++
        if (stockChanged) stats.stockChanged++
      }
    } else if (result.status === 'not_found') {
      stats.notFound++
    } else {
      stats.errors++
    }

    await updateProductPriceState(p.id, patch)
    await sleep(REQUEST_DELAY_MS)
  }

  return Response.json(stats)
}
