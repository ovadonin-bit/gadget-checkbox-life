# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

# Project overview

gadget.checkbox.life — партнёрская витрина электроники biggeek.ru через Admitad.

- Стек: Next.js 16 (App Router) + TypeScript + Tailwind v4 + Supabase
- Фото товаров: Cloudflare R2 на домене img.gadget.checkbox.life
- БД: тот же Supabase-проект что и checkbox.life, таблицы с префиксом `g_*`
- SEO: microdata (НЕ JSON-LD) по schema.org для Яндекса — Product, Offer, AggregateOffer, ItemList, BreadcrumbList
- Партнёрка: Admitad deeplink на biggeek.ru, кнопка "Купить на biggeek.ru" обязательна на карточке
- Контент: AI-генерация описаний через DeepSeek, фото и характеристики с указанием источника biggeek.ru
