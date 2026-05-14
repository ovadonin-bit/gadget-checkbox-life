import Link from 'next/link'
import { getPublishedRootCategories } from '@/lib/db'

export async function Footer() {
  const year = new Date().getFullYear()
  const cats = await getPublishedRootCategories()

  return (
    <footer className="border-t border-gray-200 mt-16">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row justify-between gap-6">
          <div>
            <div className="font-semibold text-gray-900 text-sm mb-1">
              gadget<span className="text-gray-400">.checkbox.life</span>
            </div>
            <p className="text-xs text-gray-400 max-w-xs leading-relaxed">
              Каталог электроники с актуальными ценами. Покупка через партнёра biggeek.ru.
            </p>
            <p className="text-xs text-gray-400 max-w-xs leading-relaxed mt-2">
              Фото и характеристики товаров используются с сайта biggeek.ru.
            </p>
          </div>

          <div className="flex gap-12">
            <div>
              <div className="text-xs font-medium text-gray-700 mb-2">Категории</div>
              <div className="space-y-1.5">
                {cats.map((c) => (
                  <Link key={c.slug} href={`/category/${c.slug}`} className="block text-xs text-gray-400 hover:text-gray-700">
                    {c.name}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-100 mt-8 pt-4 flex flex-col sm:flex-row justify-between gap-2 text-xs text-gray-400">
          <span>© {year} gadget.checkbox.life. Все цены носят информационный характер.</span>
          <div className="flex gap-4">
            <Link href="/privacy" className="hover:text-gray-700">Политика конфиденциальности</Link>
            <Link href="/terms" className="hover:text-gray-700">Условия использования</Link>
          </div>
        </div>
      </div>
    </footer>
  )
}
