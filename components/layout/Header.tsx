import Link from 'next/link'
import { getPublishedRootCategories } from '@/lib/db'

export async function Header() {
  const categories = await getPublishedRootCategories()

  return (
    <header className="border-b border-gray-200 bg-white sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          <Link href="/" className="font-semibold text-gray-900 text-base tracking-tight">
            gadget<span className="text-gray-400">.checkbox.life</span>
          </Link>
          <nav className="hidden sm:flex items-center gap-1">
            {categories.slice(0, 6).map((c) => (
              <Link
                key={c.slug}
                href={`/category/${c.slug}`}
                className="text-sm text-gray-500 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                {c.name}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-1 pb-2 overflow-x-auto scrollbar-none sm:hidden">
          {categories.map((c) => (
            <Link
              key={c.slug}
              href={`/category/${c.slug}`}
              className="text-xs text-gray-500 hover:text-gray-900 px-2.5 py-1 rounded-full hover:bg-gray-100 transition-colors whitespace-nowrap"
            >
              {c.name}
            </Link>
          ))}
        </div>
      </div>
    </header>
  )
}
