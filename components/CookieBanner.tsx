'use client'

import { useEffect, useState } from 'react'

export function CookieBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem('cookie_consent')) {
      setVisible(true)
    }
  }, [])

  function accept() {
    localStorage.setItem('cookie_consent', '1')
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 shadow-lg">
      <div className="max-w-5xl mx-auto px-4 py-3 flex flex-col sm:flex-row items-start sm:items-center gap-3 justify-between">
        <p className="text-xs text-gray-600 leading-relaxed">
          Чтобы улучшить работу сайта, мы используем Яндекс.Метрику и собираем файлы cookies.
          Они обрабатываются согласно условиям{' '}
          <a href="/privacy" className="underline hover:text-gray-900">
            политики конфиденциальности
          </a>
          . Продолжая работу с сайтом, вы даёте своё согласие на обработку{' '}
          <a href="/privacy" className="underline hover:text-gray-900">
            персональных данных
          </a>.
        </p>
        <button
          onClick={accept}
          className="shrink-0 bg-gray-900 text-white text-xs font-medium px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
        >
          Принять
        </button>
      </div>
    </div>
  )
}
