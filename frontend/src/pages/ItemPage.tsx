import {
  useEffect,
  useState,
} from 'react'

import { Link, useParams } from 'react-router'

import {
  getItemByPublicId,
  getItemBySlug,
} from '../api/api'
import { ApiError } from '../api/client'

import ItemGallery from '../components/ItemGallery'

import type { Item } from '../types/item'


function ItemPage() {
  const { slug, publicId } = useParams()

  const [item, setItem] = useState<Item | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)


  useEffect(() => {
    const controller = new AbortController()

    if (!slug && !publicId) {
      setError('Предмет не найден')
      setLoading(false)
      return () => controller.abort()
    }

    async function loadItem() {
      try {
        setLoading(true)
        setError(null)

        const data = publicId
          ? await getItemByPublicId(publicId, controller.signal)
          : await getItemBySlug(slug!, controller.signal)

        if (!controller.signal.aborted) {
          setItem(data)
        }
      } catch (requestError) {
        if (controller.signal.aborted) return

        if (requestError instanceof ApiError && requestError.status === 404) {
          setError('Предмет не найден')
        } else if (requestError instanceof ApiError && requestError.status === 410) {
          setError('Этот предмет временно недоступен')
        } else {
          setError('Не удалось загрузить предмет')
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadItem()
    return () => controller.abort()
  }, [slug, publicId])


  if (loading) {
    return (
      <main className="flex min-h-[70vh] items-center justify-center bg-[#efe9de]">
        <div className="text-base text-[#665f56]">
          Загружаем предмет…
        </div>
      </main>
    )
  }


  if (error || !item) {
    return (
      <main className="flex min-h-[70vh] items-center justify-center bg-[#efe9de] px-6">
        <div className="text-center">

          <p className="text-lg text-[#6e332c]">
            {error ?? 'Предмет не найден'}
          </p>

          <Link
            to="/"
            className="mt-6 inline-block text-base text-[#805c35] underline underline-offset-4"
          >
            Вернуться в справочник
          </Link>

        </div>
      </main>
    )
  }


  return (
    <main className="bg-[#efe9de] text-[#25211c]">

      <article className="mx-auto max-w-7xl px-6 py-10 lg:px-10 lg:py-16">

        {/* BACK */}
        <Link
          to="/"
          className="
            mb-10
            inline-flex
            items-center
            gap-3
            text-sm
            uppercase
            tracking-[0.16em]
            text-[#765f46]
            transition
            hover:text-[#25211c]
          "
        >
          <span>←</span>
          <span>Справочник</span>
        </Link>


        {/* MAIN */}
        <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:gap-20">

          {/* GALLERY */}
            <ItemGallery
              slug={item.slug}
              name={item.name}
              images={item.images}
            />


          {/* INFO */}
          <div className="lg:py-6">

            {item.period_text && (
              <div className="mb-5 flex items-center gap-4">

                <div className="h-px w-10 bg-[#9b764c]" />

                <span className="
                  text-sm
                  uppercase
                  tracking-[0.2em]
                  text-[#896943]
                ">
                  {item.period_text}
                </span>

              </div>
            )}


            <h1 className="
              font-display
              text-4xl
              leading-[1.02]
              tracking-[-0.025em]
              text-[#25211c]
              sm:text-5xl
              lg:text-6xl
            ">
              {item.name}
            </h1>


            {item.short_description && (
              <p className="
                mt-7
                max-w-xl
                text-xl
                leading-8
                text-[#625b52]
              ">
                {item.short_description}
              </p>
            )}


            <div className="my-10 h-px bg-[#c9beae]" />


            {/* CHARACTERISTICS */}
            <dl className="space-y-6">

              {item.creator && (
                <div className="
                  grid
                  gap-1
                  sm:grid-cols-[140px_1fr]
                  sm:gap-6
                ">

                  <dt className="text-base text-[#7c746a]">
                    Производитель
                  </dt>

                  <dd className="text-base leading-7 text-[#302b25]">
                    {item.creator}
                  </dd>

                </div>
              )}


              {item.country && (
                <div className="
                  grid
                  gap-1
                  sm:grid-cols-[140px_1fr]
                  sm:gap-6
                ">

                  <dt className="text-base text-[#7c746a]">
                    Страна
                  </dt>

                  <dd className="text-base leading-7 text-[#302b25]">
                    {item.country}
                  </dd>

                </div>
              )}


              {item.material && (
                <div className="
                  grid
                  gap-1
                  sm:grid-cols-[140px_1fr]
                  sm:gap-6
                ">

                  <dt className="text-base text-[#7c746a]">
                    Материал
                  </dt>

                  <dd className="text-base leading-7 text-[#302b25]">
                    {item.material}
                  </dd>

                </div>
              )}


              {(item.period_from || item.period_to) && (
                <div className="
                  grid
                  gap-1
                  sm:grid-cols-[140px_1fr]
                  sm:gap-6
                ">

                  <dt className="text-base text-[#7c746a]">
                    Датировка
                  </dt>

                  <dd className="text-base leading-7 text-[#302b25]">
                    {item.period_from && item.period_to
                      ? `${item.period_from}–${item.period_to}`
                      : item.period_from ?? item.period_to}
                  </dd>

                </div>
              )}


              {item.location && (
                <div className="
                  grid
                  gap-1
                  sm:grid-cols-[140px_1fr]
                  sm:gap-6
                ">

                  <dt className="text-base text-[#7c746a]">
                    Расположение
                  </dt>

                  <dd className="text-base leading-7 text-[#302b25]">
                    {item.location}
                  </dd>

                </div>
              )}

            </dl>

          </div>

        </div>


        {/* DESCRIPTION */}
        {item.description && (
          <section className="mt-20 border-t border-[#c9beae] pt-12 lg:mt-28">

            <div className="grid gap-8 lg:grid-cols-[0.7fr_1.3fr] lg:gap-20">

              <div>

                <div className="
                  mb-4
                  text-sm
                  uppercase
                  tracking-[0.2em]
                  text-[#896943]
                ">
                  О предмете
                </div>

                <h2 className="
                  font-display
                  text-3xl
                  leading-tight
                  text-[#25211c]
                  sm:text-4xl
                ">
                  История предмета
                </h2>

              </div>


              <p className="
                max-w-3xl
                text-lg
                leading-8
                text-[#514b43]
                sm:text-xl
                sm:leading-9
              ">
                {item.description}
              </p>

            </div>

          </section>
        )}


        {/* ATTRIBUTION */}
        {item.attribution_notes && (
          <section className="mt-14 lg:mt-20">

            <div className="
              border-l-2
              border-[#9b764c]
              bg-[#e7dfd2]
              px-6
              py-6
              sm:px-8
              sm:py-7
            ">

              <div className="
                text-sm
                uppercase
                tracking-[0.18em]
                text-[#896943]
              ">
                Примечание к атрибуции
              </div>

              <p className="
                mt-4
                max-w-3xl
                text-base
                leading-7
                text-[#5d564d]
              ">
                {item.attribution_notes}
              </p>

            </div>

          </section>
        )}


        {/* BOTTOM BACK */}
        <div className="mt-20 border-t border-[#c9beae] pt-8">

          <Link
            to="/"
            className="
              inline-flex
              items-center
              gap-3
              text-base
              text-[#765f46]
              transition
              hover:text-[#25211c]
            "
          >
            ← Все предметы коллекции
          </Link>

        </div>

      </article>

    </main>
  )
}

export default ItemPage