import Link from 'next/link'

export default function NotFound() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-16 text-center">
      <h1 className="text-3xl font-semibold text-gray-900 mb-3">Страница не найдена</h1>
      <p className="text-sm text-gray-600 mb-6">
        Возможно, товар или категория были удалены или ссылка устарела.
      </p>
      <Link href="/" className="inline-block bg-gray-900 hover:bg-black text-white text-sm font-medium px-5 py-2.5 rounded-xl">
        На главную
      </Link>
    </main>
  )
}
