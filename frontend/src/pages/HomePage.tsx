import {
  useEffect,
  useState,
} from 'react'

import {
  getCollections,
  getItems,
} from '../api/api'

import CollectionSection from '../components/CollectionSection'
import ItemCard from '../components/ItemCard'

import type { Collection } from '../types/collection'
import type { ItemSummary } from '../types/item'


function HomePage() {
  const [items, setItems] = useState<ItemSummary[]>([])
  const [collections, setCollections] = useState<Collection[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)


  useEffect(() => {
    const controller = new AbortController()

    async function loadData() {
      try {
        setLoading(true)
        setError(null)

        const [
          itemsData,
          collectionsData,
        ] = await Promise.all([
          getItems(controller.signal),
          getCollections(controller.signal),
        ])

        setItems(itemsData)
        setCollections(collectionsData)
      } catch {
        if (!controller.signal.aborted) {
          setError('Не удалось загрузить справочник')
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadData()
    return () => controller.abort()
  }, [reloadKey])

  const unassignedItems = items.filter(
      (item) => item.collection_id === null,
    )


  return (
    <main>

      {/* HERO */}
      <section className="bg-[#24211d] text-[#f3ede1]">

        <div className="
          mx-auto
          max-w-7xl
          px-6
          py-20
          lg:px-10
          lg:py-28
        ">

          <div className="
            grid
            gap-16
            lg:grid-cols-[1.15fr_0.85fr]
            lg:items-end
          ">

            <div>

              <div className="mb-8 flex items-center gap-4">

                <div className="h-px w-12 bg-[#a67c4b]" />

                <span className="
                  text-sm
                  uppercase
                  tracking-[0.25em]
                  text-[#cda574]
                ">
                  Коллекция отеля
                </span>

              </div>


              <h1 className="
                font-display
                max-w-4xl
                text-5xl
                leading-[0.96]
                tracking-[-0.03em]
                sm:text-6xl
                lg:text-[86px]
              ">
                Вещи помнят
                <br />
                больше, чем
                <br />
                кажется.
              </h1>

            </div>


            <div className="
              border-l
              border-[#4a433a]
              pl-8
              lg:pb-2
            ">

              <p className="
                max-w-md
                text-lg
                leading-8
                text-[#d2c8bb]
                lg:text-xl
                lg:leading-9
              ">
                Исторические предметы,
                сохранившиеся в интерьерах отеля.
                История, происхождение и детали
                каждого экспоната.
              </p>


              <div className="mt-9 flex items-start gap-4">

                <div className="
                  mt-3
                  h-px
                  w-8
                  shrink-0
                  bg-[#765b3b]
                " />

                <div className="
                  text-sm
                  uppercase
                  leading-6
                  tracking-[0.16em]
                  text-[#b09c85]
                ">
                  Выберите коллекцию ниже
                  <br />
                  или откройте предмет по QR-коду
                </div>

              </div>

            </div>

          </div>

        </div>

      </section>


      {/* DIRECTORY */}
      <section className="bg-[#efe9de]">

        <div className="
          mx-auto
          max-w-7xl
          px-6
          py-16
          lg:px-10
          lg:py-24
        ">

          <div className="
            mb-8
            flex
            items-end
            justify-between
            gap-8
          ">

            <div>

              <div className="
                text-sm
                uppercase
                tracking-[0.22em]
                text-[#896943]
              ">
                Справочник
              </div>

              <h2 className="
                font-display
                mt-3
                text-4xl
                tracking-tight
                text-[#25211c]
                sm:text-5xl
              ">
                Коллекции
              </h2>

            </div>


            {!loading && (
              <div className="
                pb-1
                text-base
                text-[#665f56]
              ">
                {items.length} предметов
              </div>
            )}

          </div>


          {loading && (
            <div className="
              border-t
              border-[#c9beae]
              py-24
              text-center
              text-base
              text-[#756e65]
            ">
              Загружаем коллекцию…
            </div>
          )}


          {error && (
            <div className="border-t border-[#c9beae] py-24 text-center text-lg text-red-900" role="alert">
              <p>{error}</p>
              <button
                type="button"
                onClick={() => setReloadKey((value) => value + 1)}
                className="mt-5 rounded border border-[#805c35] px-4 py-2 text-sm text-[#805c35]"
              >
                Повторить
              </button>
            </div>
          )}


          {!loading && !error && (
              <div className="border-t border-[#c9beae]">

                {collections.map((collection) => {
                  const collectionItems = items.filter(
                    (item) =>
                      item.collection_id === collection.id,
                  )

                  return (
                    <CollectionSection
                      key={collection.id}
                      collection={collection}
                      items={collectionItems}
                    />
                  )
                })}

                {unassignedItems.length > 0 && (
                  <section className="border-b border-[#c9beae] py-10">

                    <div className="mb-10">

                      <div className="
                        text-sm
                        uppercase
                        tracking-[0.18em]
                        text-[#896943]
                      ">
                        Каталог
                      </div>

                      <h2 className="
                        font-display
                        mt-2
                        text-3xl
                        leading-tight
                        text-[#25211c]
                        sm:text-4xl
                      ">
                        Отдельные предметы
                      </h2>

                      <p className="
                        mt-3
                        max-w-2xl
                        text-base
                        leading-7
                        text-[#756e65]
                      ">
                        Экспонаты, не входящие в отдельную коллекцию.
                      </p>

                    </div>

                    <div className="
                      grid
                      gap-x-10
                      gap-y-16
                      md:grid-cols-2
                    ">
                      {unassignedItems.map((item) => (
                        <ItemCard
                          key={item.id}
                          item={item}
                        />
                      ))}
                    </div>

                  </section>
                )}

              </div>
            )}

        </div>

      </section>

    </main>
  )
}

export default HomePage