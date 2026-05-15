"use client"
import { useState, useEffect, useCallback, useRef } from 'react'
import Image from 'next/image'

interface Props {
  images: string[]
  productName: string
}

export function ImageGallery({ images, productName }: Props) {
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [current, setCurrent] = useState(0)
  const touchStartX = useRef<number | null>(null)
  const touchStartY = useRef<number | null>(null)

  const open = (index: number) => {
    setCurrent(index)
    setLightboxOpen(true)
  }
  const close = () => setLightboxOpen(false)
  const prev = useCallback(() => setCurrent(i => (i - 1 + images.length) % images.length), [images.length])
  const next = useCallback(() => setCurrent(i => (i + 1) % images.length), [images.length])

  useEffect(() => {
    if (!lightboxOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
      else if (e.key === 'ArrowLeft') prev()
      else if (e.key === 'ArrowRight') next()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lightboxOpen, prev, next])

  useEffect(() => {
    document.body.style.overflow = lightboxOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [lightboxOpen])

  const onTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length !== 1) return
    touchStartX.current = e.touches[0].clientX
    touchStartY.current = e.touches[0].clientY
  }
  const onTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null || touchStartY.current === null) return
    const dx = touchStartX.current - e.changedTouches[0].clientX
    const dy = touchStartY.current - e.changedTouches[0].clientY
    // Only treat as swipe if horizontal movement dominates and exceeds threshold
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      dx > 0 ? next() : prev()
    }
    touchStartX.current = null
    touchStartY.current = null
  }

  return (
    <>
      {/* Main image */}
      <div
        className="aspect-square bg-gray-50 rounded-2xl overflow-hidden relative mb-3 cursor-zoom-in"
        onClick={() => open(0)}
        role="button"
        aria-label="Открыть галерею"
      >
        {images[0] ? (
          <Image
            src={images[0]}
            alt={productName}
            fill
            sizes="(max-width: 768px) 100vw, 50vw"
            className="object-contain p-6"
            itemProp="image"
            priority
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-gray-300 text-sm">
            Нет фото
          </div>
        )}
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div className="grid grid-cols-5 gap-2">
          {images.slice(1, 6).map((url, i) => (
            <div
              key={i}
              className="aspect-square bg-gray-50 rounded-lg overflow-hidden relative cursor-zoom-in"
              onClick={() => open(i + 1)}
              role="button"
              aria-label={`Фото ${i + 2}`}
            >
              <Image
                src={url}
                alt={`${productName} — фото ${i + 2}`}
                fill
                sizes="20vw"
                className="object-contain p-2"
              />
            </div>
          ))}
        </div>
      )}

      {/* Lightbox */}
      {lightboxOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/92 flex items-center justify-center"
          onClick={close}
          onTouchStart={onTouchStart}
          onTouchEnd={onTouchEnd}
        >
          {/* Close */}
          <button
            className="absolute top-4 right-4 text-white/80 hover:text-white text-2xl w-10 h-10 flex items-center justify-center z-10 bg-black/30 rounded-full transition-colors"
            onClick={close}
            aria-label="Закрыть"
          >
            ✕
          </button>

          {/* Prev */}
          {images.length > 1 && (
            <button
              className="absolute left-3 top-1/2 -translate-y-1/2 text-white/80 hover:text-white text-3xl w-11 h-11 flex items-center justify-center z-10 bg-black/30 hover:bg-black/50 rounded-full transition-colors"
              onClick={e => { e.stopPropagation(); prev() }}
              aria-label="Предыдущее"
            >
              ‹
            </button>
          )}

          {/* Image area — click doesn't close */}
          <div
            className="relative w-full h-full"
            style={{ padding: '56px 64px' }}
            onClick={e => e.stopPropagation()}
          >
            <Image
              src={images[current]}
              alt={`${productName} — фото ${current + 1}`}
              fill
              sizes="100vw"
              className="object-contain"
              style={{ touchAction: 'pinch-zoom' }}
              priority
            />
          </div>

          {/* Next */}
          {images.length > 1 && (
            <button
              className="absolute right-3 top-1/2 -translate-y-1/2 text-white/80 hover:text-white text-3xl w-11 h-11 flex items-center justify-center z-10 bg-black/30 hover:bg-black/50 rounded-full transition-colors"
              onClick={e => { e.stopPropagation(); next() }}
              aria-label="Следующее"
            >
              ›
            </button>
          )}

          {/* Counter + dots */}
          {images.length > 1 && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 z-10">
              {images.slice(0, 10).map((_, i) => (
                <button
                  key={i}
                  className={`w-1.5 h-1.5 rounded-full transition-all ${i === current ? 'bg-white scale-125' : 'bg-white/40'}`}
                  onClick={e => { e.stopPropagation(); setCurrent(i) }}
                  aria-label={`Фото ${i + 1}`}
                />
              ))}
              {images.length > 10 && (
                <span className="text-white/60 text-xs ml-1">{current + 1}/{images.length}</span>
              )}
            </div>
          )}
        </div>
      )}
    </>
  )
}
