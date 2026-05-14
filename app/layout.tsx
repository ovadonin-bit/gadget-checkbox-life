import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Script from 'next/script'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import './globals.css'

const inter = Inter({
  subsets: ['latin', 'cyrillic'],
  variable: '--font-inter',
})

export const metadata: Metadata = {
  title: {
    default: 'gadget.checkbox.life — каталог электроники с актуальными ценами',
    template: '%s | gadget.checkbox.life',
  },
  description:
    'Каталог смартфонов, ноутбуков, планшетов и аксессуаров с описанием, характеристиками и актуальными ценами. Покупка через партнёра biggeek.ru.',
  metadataBase: new URL('https://gadget.checkbox.life'),
  openGraph: {
    siteName: 'gadget.checkbox.life',
    locale: 'ru_RU',
    type: 'website',
  },
  robots: {
    index: true,
    follow: true,
  },
  verification: {
    yandex: 'fc0133f625235ecf',
    other: {
      'verify-admitad': 'd0422e258a',
      'yandex-market': '9hf6yr1rus1au57a',
      'takprodam-verification': 'a237ad06-af64-43d4-b346-0deef7c0f0be',
    },
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // TODO: заменить ID счётчика Метрики на новый, когда зарегистрируете для gadget.checkbox.life
  const YANDEX_METRIKA_ID = process.env.NEXT_PUBLIC_YANDEX_METRIKA_ID

  return (
    <html lang="ru" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-white text-gray-900">
        {YANDEX_METRIKA_ID && (
          <>
            <Script id="yandex-metrika" strategy="afterInteractive">{`
              (function(m,e,t,r,i,k,a){
                m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
                m[i].l=1*new Date();
                for(var j=0;j<document.scripts.length;j++){if(document.scripts[j].src===r){return;}}
                k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)
              })(window,document,'script','https://mc.yandex.ru/metrika/tag.js?id=${YANDEX_METRIKA_ID}','ym');
              ym(${YANDEX_METRIKA_ID},'init',{ssr:true,clickmap:true,ecommerce:"dataLayer",referrer:document.referrer,url:location.href,accurateTrackBounce:true,trackLinks:true});
            `}</Script>
            <noscript>
              <div>
                <img src={`https://mc.yandex.ru/watch/${YANDEX_METRIKA_ID}`} style={{position:'absolute',left:'-9999px'}} alt="" />
              </div>
            </noscript>
          </>
        )}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'WebSite',
            name: 'gadget.checkbox.life',
            url: 'https://gadget.checkbox.life',
            description: 'Каталог электроники с актуальными ценами. Покупка через партнёра biggeek.ru.',
            inLanguage: 'ru-RU',
            publisher: {
              '@type': 'Organization',
              name: 'gadget.checkbox.life',
              url: 'https://gadget.checkbox.life',
            },
          }) }}
        />
        <Header />
        <div className="flex-1">{children}</div>
        <Footer />
      </body>
    </html>
  )
}
