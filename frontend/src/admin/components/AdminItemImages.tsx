import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
} from 'react'

import { useNavigate } from 'react-router'

import {
  deleteAdminItemImage,
  getAdminItemImages,
  getAdminItemImageUrl,
  reorderAdminItemImages,
  setAdminItemPrimaryImage,
  uploadAdminItemImage,
} from '../api/images'

import type { AdminItemImage } from '../types/image'


interface AdminItemImagesProps {
  itemId: number
}


function AdminItemImages({
  itemId,
}: AdminItemImagesProps) {
  const navigate = useNavigate()

  const fileInputRef =
    useRef<HTMLInputElement | null>(null)

  const [images, setImages] =
    useState<AdminItemImage[]>([])

  const [isLoading, setIsLoading] =
    useState(true)

  const [isUploading, setIsUploading] =
    useState(false)

  const [busyImageId, setBusyImageId] =
    useState<number | null>(null)

  const [error, setError] =
    useState<string | null>(null)


  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    async function loadImages() {
      try {
        const loaded =
          await getAdminItemImages(itemId, controller.signal)

        if (!cancelled) {
          setImages(loaded)
        }
      } catch (error) {
        if (cancelled) {
          return
        }

        handleRequestError(error)
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadImages()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [itemId])


  function handleRequestError(
    error: unknown,
  ) {
    if (
      error instanceof Error &&
      error.message === 'UNAUTHORIZED'
    ) {
      navigate(
        '/admin/login',
        {
          replace: true,
        },
      )

      return
    }

    setError(
      'Не удалось выполнить операцию с фотографиями.',
    )
  }


  async function handleFileChange(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file =
      event.target.files?.[0]

    if (!file) {
      return
    }

    setError(null)
    setIsUploading(true)

    try {
      const uploaded =
        await uploadAdminItemImage(
          itemId,
          file,
        )

      setImages((current) => [
        ...current,
        uploaded,
      ])
    } catch (error) {
      if (
        error instanceof Error &&
        error.message === 'IMAGE_TOO_LARGE'
      ) {
        setError(
          'Файл слишком большой.',
        )
      } else if (
        error instanceof Error &&
        error.message === 'INVALID_IMAGE'
      ) {
        setError(
          'Файл не является допустимым изображением.',
        )
      } else {
        handleRequestError(error)
      }
    } finally {
      setIsUploading(false)

      // Позволяет выбрать тот же файл повторно.
      event.target.value = ''
    }
  }


  async function handleSetPrimary(
    imageId: number,
  ) {
    setError(null)
    setBusyImageId(imageId)

    try {
      await setAdminItemPrimaryImage(
        itemId,
        imageId,
      )

      setImages((current) =>
        current.map((image) => ({
          ...image,
          is_primary:
            image.id === imageId,
        })),
      )
    } catch (error) {
      handleRequestError(error)
    } finally {
      setBusyImageId(null)
    }
  }


  async function handleDelete(
    image: AdminItemImage,
  ) {
    const confirmed = window.confirm(
      `Удалить фотографию "${image.original_filename}"?`,
    )

    if (!confirmed) {
      return
    }

    setError(null)
    setBusyImageId(image.id)

    try {
      await deleteAdminItemImage(
        itemId,
        image.id,
      )

      const remaining =
        images.filter(
          (current) =>
            current.id !== image.id,
        )

      /*
       * Если удалили primary, backend сам выбрал
       * новую primary. Чтобы frontend не пытался
       * угадывать, перечитываем актуальное состояние.
       */
      if (image.is_primary) {
        const refreshed =
          await getAdminItemImages(itemId)

        setImages(refreshed)
      } else {
        setImages(remaining)
      }
    } catch (error) {
      handleRequestError(error)
    } finally {
      setBusyImageId(null)
    }
  }


  async function handleMove(
    imageId: number,
    direction: 'up' | 'down',
  ) {
    const currentIndex =
      images.findIndex(
        (image) =>
          image.id === imageId,
      )

    if (currentIndex === -1) {
      return
    }

    const targetIndex =
      direction === 'up'
        ? currentIndex - 1
        : currentIndex + 1

    if (
      targetIndex < 0 ||
      targetIndex >= images.length
    ) {
      return
    }

    const reordered = [...images]

    const [
      movedImage,
    ] = reordered.splice(
      currentIndex,
      1,
    )

    reordered.splice(
      targetIndex,
      0,
      movedImage,
    )

    setError(null)
    setBusyImageId(imageId)

    try {
      const saved =
        await reorderAdminItemImages(
          itemId,
          reordered.map(
            (image) => image.id,
          ),
        )

      setImages(saved)
    } catch (error) {
      handleRequestError(error)
    } finally {
      setBusyImageId(null)
    }
  }


  if (isLoading) {
    return (
      <section className="rounded-xl border border-stone-800 bg-stone-900/40 p-6">
        <p className="text-stone-400">
          Загрузка фотографий...
        </p>
      </section>
    )
  }


  return (
    <section className="rounded-xl border border-stone-800 bg-stone-900/40 p-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h2 className="text-lg font-medium">
            Фотографии
          </h2>

          <p className="mt-2 text-sm text-stone-500">
            Первая фотография автоматически
            становится главной.
          </p>
        </div>

        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            className="hidden"
          />

          <button
            type="button"
            disabled={isUploading}
            onClick={() =>
              fileInputRef.current?.click()
            }
            className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium transition hover:bg-amber-600 disabled:opacity-50"
          >
            {isUploading
              ? 'Загрузка...'
              : 'Добавить фотографию'}
          </button>
        </div>
      </div>

      {error && (
        <p className="mt-5 rounded-lg border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {images.length === 0 ? (
        <div className="mt-6 rounded-lg border border-dashed border-stone-800 px-6 py-12 text-center text-sm text-stone-500">
          У предмета пока нет фотографий.
        </div>
      ) : (
        <div className="mt-6 space-y-3">
          {images.map(
            (image, index) => (
              <div
                key={image.id}
                className="flex items-center gap-5 rounded-xl border border-stone-800 bg-stone-950/60 p-4"
              >
                <img
                  src={getAdminItemImageUrl(
                    itemId,
                    image.id,
                  ) ?? undefined
                }
                  alt={image.original_filename ?? 'Без названия'}
                  className="h-24 w-24 shrink-0 rounded-lg object-cover"
                />

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-3">
                    <p className="truncate font-medium">
                      {image.original_filename}
                    </p>

                    {image.is_primary && (
                      <span className="rounded-full bg-amber-950 px-2.5 py-1 text-xs text-amber-400">
                        Главная
                      </span>
                    )}
                  </div>

                  <p className="mt-2 text-xs text-stone-600">
                      {image.size !== null
                        ? formatBytes(image.size)
                        : 'Размер неизвестен'}
                      {' · '}
                      позиция {index + 1}
                    </p>

                  {!image.is_primary && (
                    <button
                      type="button"
                      disabled={
                        busyImageId === image.id
                      }
                      onClick={() =>
                        handleSetPrimary(
                          image.id,
                        )
                      }
                      className="mt-3 text-sm text-amber-600 hover:text-amber-500 disabled:opacity-50"
                    >
                      Сделать главной
                    </button>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    title="Переместить выше"
                    disabled={
                      index === 0 ||
                      busyImageId !== null
                    }
                    onClick={() =>
                      handleMove(
                        image.id,
                        'up',
                      )
                    }
                    className="rounded-lg border border-stone-700 px-3 py-2 text-stone-300 hover:border-stone-500 disabled:opacity-30"
                  >
                    ↑
                  </button>

                  <button
                    type="button"
                    title="Переместить ниже"
                    disabled={
                      index ===
                        images.length - 1 ||
                      busyImageId !== null
                    }
                    onClick={() =>
                      handleMove(
                        image.id,
                        'down',
                      )
                    }
                    className="rounded-lg border border-stone-700 px-3 py-2 text-stone-300 hover:border-stone-500 disabled:opacity-30"
                  >
                    ↓
                  </button>

                  <button
                    type="button"
                    disabled={
                      busyImageId !== null
                    }
                    onClick={() =>
                      handleDelete(image)
                    }
                    className="rounded-lg border border-red-900 px-3 py-2 text-sm text-red-400 transition hover:bg-red-950/40 disabled:opacity-50"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ),
          )}
        </div>
      )}
    </section>
  )
}


function formatBytes(
  bytes: number,
): string {
  if (bytes < 1024) {
    return `${bytes} Б`
  }

  if (bytes < 1024 * 1024) {
    return `${(
      bytes / 1024
    ).toFixed(1)} КБ`
  }

  return `${(
    bytes /
    (1024 * 1024)
  ).toFixed(1)} МБ`
}


export default AdminItemImages