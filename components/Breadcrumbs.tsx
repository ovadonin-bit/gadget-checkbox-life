import Link from 'next/link'

export interface Crumb {
  name: string
  href: string
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav
      aria-label="Хлебные крошки"
      itemScope
      itemType="https://schema.org/BreadcrumbList"
      className="text-xs text-gray-500 mb-4 overflow-x-auto scrollbar-none"
    >
      <ol className="flex items-center gap-1.5 whitespace-nowrap">
        {items.map((c, i) => (
          <li
            key={c.href}
            itemProp="itemListElement"
            itemScope
            itemType="https://schema.org/ListItem"
            className="flex items-center gap-1.5"
          >
            {i < items.length - 1 ? (
              <Link itemProp="item" href={c.href} className="hover:text-gray-900">
                <span itemProp="name">{c.name}</span>
              </Link>
            ) : (
              <span itemProp="item" className="text-gray-900">
                <span itemProp="name">{c.name}</span>
              </span>
            )}
            <meta itemProp="position" content={String(i + 1)} />
            {i < items.length - 1 && <span className="text-gray-300">/</span>}
          </li>
        ))}
      </ol>
    </nav>
  )
}
