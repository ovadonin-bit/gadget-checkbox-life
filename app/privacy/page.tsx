import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Политика конфиденциальности',
  robots: { index: false, follow: true },
}

export default function PrivacyPage() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-semibold text-gray-900 mb-4">Политика конфиденциальности</h1>
      <div className="product-description text-sm text-gray-700 space-y-3">
        <p>
          Сайт gadget.checkbox.life не собирает персональные данные пользователей.
          Используется Яндекс.Метрика для анонимной аналитики посещений.
        </p>
        <p>
          При переходе по партнёрской ссылке на biggeek.ru дальнейшее взаимодействие
          (оформление заказа, оплата, обработка персональных данных) происходит на стороне biggeek.ru
          и регулируется политикой конфиденциальности этого магазина.
        </p>
        <p>
          Контакты: ov.adonin@gmail.com
        </p>
      </div>
    </main>
  )
}
