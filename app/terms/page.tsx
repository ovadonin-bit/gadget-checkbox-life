import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Условия использования',
  robots: { index: false, follow: true },
}

export default function TermsPage() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-semibold text-gray-900 mb-4">Условия использования</h1>
      <div className="product-description text-sm text-gray-700 space-y-3">
        <p>
          gadget.checkbox.life — информационный каталог электроники.
          Сайт не является интернет-магазином и не осуществляет продажу товаров напрямую.
        </p>
        <p>
          Все цены и наличие, указанные на сайте, носят информационный характер
          и могут отличаться от актуальных значений на сайте продавца (biggeek.ru).
          Точную информацию уточняйте на странице товара продавца.
        </p>
        <p>
          Фотографии и характеристики товаров используются с сайта biggeek.ru
          с указанием источника. Описания товаров — оригинальные.
        </p>
        <p>
          Покупка осуществляется через партнёрскую программу Admitad на сайте biggeek.ru.
          За использование партнёрской ссылки покупатель не несёт дополнительных расходов.
        </p>
      </div>
    </main>
  )
}
