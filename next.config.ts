import type { NextConfig } from 'next'
import path from 'path'

const nextConfig: NextConfig = {
  output: 'standalone',
  experimental: {
    cpus: 2,
  },
  turbopack: {
    root: path.resolve(__dirname),
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**.biggeek.ru' },
      { protocol: 'https', hostname: 'biggeek.ru' },
      { protocol: 'https', hostname: 'img.gadget.checkbox.life' },
      { protocol: 'https', hostname: '*.s3.timeweb.cloud' },
    ],
    formats: ['image/webp'],
  },
}

export default nextConfig
