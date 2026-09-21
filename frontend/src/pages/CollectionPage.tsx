import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  Link,
  useParams,
} from 'react-router'

import {
  getCollectionBySlug,
  getItems,
} from '../api/api'

import { ApiError } from '../api/client'

import ItemCard from '../components/ItemCard'

import type { Collection } from '../types/collection'
import type { ItemSummary } from '../types/item'

import { useSite } from '../site/SiteContext'


function CollectionPage() {
  const { hotelName } = useSite()
  const { slug } = useParams()

  const [collection, setCollection] = useState<Collection | null>(null)
  const [items, setItems] = useState<ItemSummary[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)


  useEffect(() => {
    const controller = new AbortController()

    if (!slug) {
      setError('Коллекция не найдена')
      setLoading(false)

      return () => controller.abort()
    }


    async function loadCollection() {
      try {
        setLoading(true)
        setError(null)

        const [
          collectionData,
          itemsData,
        ] = await Promise.all([
          getCollectionBySlug(
            slug!,
            controller.signal,
          ),

          getItems(
            controller.signal,
          ),
        ])


        if (controller.signal.aborted) {
          return
        }

        setCollection(collectionData)
        setItems(itemsData)

      } catch (requestError) {
        if (controller.signal.aborted) {
          return
        }

        if (
          requestError instanceof ApiError
          && requestError.status === 404
        ) {
          setError('Коллекция не найдена')
        } else {
          setError('Не удалось загрузить коллекцию')
        }

      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }


    void loadCollection()

    return () => controller.abort()

  }, [slug])


  const collectionItems = useMemo(() => {
    if (!collection) {
      return []
    }

    return items
      .filter(
        (item) =>
          item.collection_id === collection.id,
      )
      .sort(
        (a, b) =>
          a.sort_order - b.sort_order
          || a.id - b.id,
      )

  }, [
    collection,
    items,
  ])


  useEffect(() => {
    if (!collection) {
      return
    }

    const previousTitle = document.title

    const descriptionTag =
      document.querySelector<HTMLMetaElement>(
        'meta[name="description"]',
      )

    const previousDescription =
      descriptionTag?.content ?? null


    document.title =
      `${collection.name} — Отель «${hotelName}»`


    if (descriptionTag) {
      descriptionTag.content =
        collection.description
        ?? `Предметы экспозиции «${collection.name}».`
    }


    return () => {
      document.title = previousTitle

      if (
        descriptionTag
        && previousDescription !== null
      ) {
        descriptionTag.content =
          previousDescription
      }
    }

  }, [
    collection,
    hotelName,
  ])


  if (loading) {
    return (
      <main
        className="
          flex
          min-h-[70vh]
          items-center
          justify-center
          bg-[#efe9de]
        "
      >
        <div className="text-base text-[#665f56]">
          Загружаем коллекцию…
        </div>
      </main>
    )
  }


  if (error || !collection) {
    return (
      <main
        className="
          flex
          min-h-[70vh]
          items-center
          justify-center
          bg-[#efe9de]
          px-6
        "
      >
        <div className="text-center">

          <p
            role="alert"
            aria-live="polite"
            className="text-lg text-[#6e332c]"
          >
            {error ?? 'Коллекция не найдена'}
          </p>


          <Link
            to="/"
            className="
              mt-6
              inline-block
              text-base
              text-[#805c35]
              underline
              underline-offset-4
            "
          >
            Вернуться в справочник
          </Link>

        </div>
      </main>
    )
  }


  return (
    <main className="bg-[#efe9de] text-[#25211c]">

      <section
        className="
          mx-auto
          max-w-7xl
          px-6
          py-10
          lg:px-10
          lg:py-16
        "
      >

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


        {/* HEADER */}
        <header
          className="
            mb-14
            border-b
            border-[#c9beae]
            pb-10
          "
        >

          <div
            className="
              mb-5
              flex
              items-center
              gap-4
            "
          >

            <div className="h-px w-10 bg-[#9b764c]" />

            <span
              className="
                text-sm
                uppercase
                tracking-[0.2em]
                text-[#896943]
              "
            >
              Коллекция
            </span>

          </div>


          <h1
            className="
              font-display
              max-w-4xl
              text-4xl
              leading-[1.02]
              tracking-[-0.025em]
              text-[#25211c]
              sm:text-5xl
              lg:text-6xl
            "
          >
            {collection.name}
          </h1>


          {collection.location && (
            <p
              className="
                mt-5
                text-base
                uppercase
                tracking-[0.12em]
                text-[#896943]
              "
            >
              {collection.location}
            </p>
          )}


          {collection.description && (
            <p
              className="
                mt-7
                max-w-3xl
                text-lg
                leading-8
                text-[#625b52]
              "
            >
              {collection.description}
            </p>
          )}


          <div
            className="
              mt-8
              text-sm
              uppercase
              tracking-[0.15em]
              text-[#756e65]
            "
          >
            {collectionItems.length}{' '}
            {
              collectionItems.length === 1
                ? 'предмет'
                : 'предметов'
            }
          </div>

        </header>


        {/* ITEMS */}
        {collectionItems.length > 0 ? (

          <div
            className="
              grid
              gap-x-10
              gap-y-16
              md:grid-cols-2
            "
          >
            {collectionItems.map((item) => (
              <ItemCard
                key={item.id}
                item={item}
              />
            ))}
          </div>

        ) : (

          <div
            className="
              py-20
              text-center
              text-lg
              text-[#756e65]
            "
          >
            В этой коллекции пока нет предметов.
          </div>

        )}

      </section>

    </main>
  )
}


export default CollectionPage