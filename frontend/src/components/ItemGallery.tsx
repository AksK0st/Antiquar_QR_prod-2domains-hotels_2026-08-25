import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import {
  getItemImageByIdUrl,
} from '../api/api'

import type {
  ItemImage,
} from '../types/item'


interface ItemGalleryProps {
  name: string
  images: ItemImage[]
}


function ItemGallery({
  name,
  images,
}: ItemGalleryProps) {
  const sortedImages = useMemo(
    () =>
      [...images].sort(
        (a, b) =>
          a.sort_order - b.sort_order ||
          a.id - b.id,
      ),
    [images],
  )

  const primaryIndex = Math.max(
    0,
    sortedImages.findIndex(
      (image) => image.is_primary,
    ),
  )

  const [activeIndex, setActiveIndex] =
    useState(primaryIndex)

  const touchStartX =
    useRef<number | null>(null)


  useEffect(() => {
    setActiveIndex(primaryIndex)
  }, [primaryIndex])


  if (sortedImages.length === 0) {
    return (
      <div className="flex min-h-[420px] items-center justify-center bg-[#d9d0c2] p-8">
        <p className="text-sm text-[#756e65]">
          Фотография пока не добавлена
        </p>
      </div>
    )
  }


  const activeImage =
    sortedImages[activeIndex]

  const hasMultipleImages =
    sortedImages.length > 1


  function showPrevious() {
    setActiveIndex((current) =>
      current === 0
        ? sortedImages.length - 1
        : current - 1,
    )
  }


  function showNext() {
    setActiveIndex((current) =>
      current ===
      sortedImages.length - 1
        ? 0
        : current + 1,
    )
  }


  function handleTouchStart(
    event: React.TouchEvent,
  ) {
    touchStartX.current =
      event.touches[0].clientX
  }


  function handleTouchEnd(
    event: React.TouchEvent,
  ) {
    if (
      touchStartX.current === null
    ) {
      return
    }

    const endX =
      event.changedTouches[0].clientX

    const distance =
      endX - touchStartX.current

    touchStartX.current = null

    /*
     * Небольшие движения пальца
     * считаем обычным касанием,
     * а не свайпом.
     */
    if (Math.abs(distance) < 50) {
      return
    }

    if (distance > 0) {
      showPrevious()
    } else {
      showNext()
    }
  }


  return (
    <div>
      <div
        className="relative bg-[#d9d0c2] p-4 sm:p-8 lg:p-10"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        tabIndex={0}
        aria-label={`Галерея: ${name}`}
        onKeyDown={(event) => {
          if (event.key === 'ArrowLeft') { event.preventDefault(); showPrevious() }
          if (event.key === 'ArrowRight') { event.preventDefault(); showNext() }
        }}
      >
        <img
          key={activeImage.id}
          src={getItemImageByIdUrl(
            activeImage.id,
            activeImage.content_version,
          )}
          alt={`${name} — фото ${activeIndex + 1}`}
          width={activeImage.width ?? undefined}
          height={activeImage.height ?? undefined}
          className="
            mx-auto
            max-h-[760px]
            min-h-[420px]
            w-full
            object-contain
          "
        />

        {hasMultipleImages && (
          <>
            <button
              type="button"
              onClick={showPrevious}
              aria-label="Предыдущая фотография"
              className="
                absolute
                left-3
                top-1/2
                flex
                h-11
                w-11
                -translate-y-1/2
                items-center
                justify-center
                rounded-full
                bg-[#24211d]/85
                text-xl
                text-[#f3ede1]
                transition
                hover:bg-[#24211d]
                sm:left-5
              "
            >
              ←
            </button>

            <button
              type="button"
              onClick={showNext}
              aria-label="Следующая фотография"
              className="
                absolute
                right-3
                top-1/2
                flex
                h-11
                w-11
                -translate-y-1/2
                items-center
                justify-center
                rounded-full
                bg-[#24211d]/85
                text-xl
                text-[#f3ede1]
                transition
                hover:bg-[#24211d]
                sm:right-5
              "
            >
              →
            </button>

            <div
              aria-live="polite"
              className="
              absolute
              bottom-3
              right-3
              rounded-full
              bg-[#24211d]/85
              px-3
              py-1.5
              text-xs
              tracking-[0.08em]
              text-[#f3ede1]
              sm:bottom-5
              sm:right-5
            ">
              {activeIndex + 1}
              {' / '}
              {sortedImages.length}
            </div>
          </>
        )}
      </div>

      {hasMultipleImages && (
        <div className="
          mt-4
          flex
          gap-3
          overflow-x-auto
          pb-2
        ">
          {sortedImages.map(
            (image, index) => {
              const isActive =
                index === activeIndex

              return (
                <button
                  key={image.id}
                  type="button"
                  onClick={() =>
                    setActiveIndex(index)
                  }
                  aria-label={
                    `Открыть фотографию ${index + 1}`
                  }
                  className={`
                    h-20
                    w-24
                    shrink-0
                    overflow-hidden
                    border-2
                    bg-[#d9d0c2]
                    transition
                    ${
                      isActive
                        ? 'border-[#896943]'
                        : 'border-transparent opacity-65 hover:opacity-100'
                    }
                  `}
                >
                  <img
                    src={getItemImageByIdUrl(
                      image.id,
                      image.content_version,
                    )}
                    alt=""
                    loading="lazy"
                    className="
                      h-full
                      w-full
                      object-cover
                    "
                  />
                </button>
              )
            },
          )}
        </div>
      )}
    </div>
  )
}


export default ItemGallery