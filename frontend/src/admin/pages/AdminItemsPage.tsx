import {
  useEffect,
  useState,
} from 'react'

import {
  Link,
  useNavigate,
} from 'react-router'

import {
  getAdminItems,
  setItemActive,
} from '../api/items'
import { getAdminCollections } from '../api/collections'
import { getAdminSites, type AdminSite } from '../api/sites'

import type { AdminCollection } from '../types/collection'
import type { AdminItem } from '../types/item'

const PAGE_SIZE = 50


function AdminItemsPage() {
  const navigate = useNavigate()

  const [items, setItems] =
    useState<AdminItem[]>([])

  const [isLoading, setIsLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const [updatingId, setUpdatingId] =
    useState<number | null>(null)
  const [searchInput, setSearchInput] = useState('')
  const [submittedSearch, setSubmittedSearch] = useState('')
  const [collectionFilter, setCollectionFilter] = useState('')
  const [hotelFilter, setHotelFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [collections, setCollections] = useState<AdminCollection[]>([])
  const [sites, setSites] = useState<AdminSite[]>([])
  const [reloadKey, setReloadKey] = useState(0)
  const [page, setPage] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    async function loadItems() {
      setIsLoading(true)
      setError(null)
      try {
        const loadedItems =
          await getAdminItems({
            q: submittedSearch || undefined,
            hotelName: hotelFilter || undefined,
            collectionId: collectionFilter ? Number(collectionFilter) : undefined,
            isActive: statusFilter === 'active' ? true : statusFilter === 'inactive' ? false : undefined,
            limit: PAGE_SIZE,
            offset: page * PAGE_SIZE,
            signal: controller.signal,
          })

        if (!cancelled) {
          setItems(loadedItems)
        }
      } catch (error) {
        if (cancelled) {
          return
        }

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
          'Не удалось загрузить предметы.',
        )
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadItems()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [collectionFilter, hotelFilter, navigate, reloadKey, page, statusFilter, submittedSearch])

  useEffect(() => {
    const controller = new AbortController()

    Promise.all([
      getAdminCollections({ limit: 200, signal: controller.signal }),
      getAdminSites(controller.signal),
    ])
      .then(([loadedCollections, loadedSites]) => {
        setCollections(loadedCollections)
        setSites(loadedSites)
      })
      .catch((requestError) => {
        if (controller.signal.aborted) return
        if (requestError instanceof Error && requestError.message === 'UNAUTHORIZED') {
          navigate('/admin/login', { replace: true })
        }
      })

    return () => controller.abort()
  }, [navigate])



  async function handleToggleActive(
    item: AdminItem,
  ) {
    setUpdatingId(item.id)
    setError(null)

    try {
      const updated = await setItemActive(
        item,
        !item.is_active,
      )

      setItems((currentItems) =>
        currentItems.map((currentItem) =>
          currentItem.id === updated.id
            ? updated
            : currentItem,
        ),
      )
    } catch (error) {
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
        error instanceof Error && error.message === 'VERSION_CONFLICT'
          ? 'Предмет уже изменён в другой вкладке. Обновите список.'
          : 'Не удалось изменить состояние предмета.',
      )
    } finally {
      setUpdatingId(null)
    }
  }


  if (isLoading) {
    return (
      <p className="text-stone-400">
        Загрузка предметов...
      </p>
    )
  }


  return (
    <div>
      <div className="flex items-start justify-between gap-6">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-amber-600">
            Каталог
          </p>

          <h1 className="mt-2 text-3xl font-semibold">
            Предметы
          </h1>

          <p className="mt-3 text-sm text-stone-400">
            Управление экспонатами каталога.
          </p>
        </div>

        <Link
          to="/admin/items/new"
          className="rounded-lg bg-amber-700 px-4 py-3 text-sm font-medium transition hover:bg-amber-600"
        >
          Добавить предмет
        </Link>
      </div>

      <form
        className="mt-6 flex flex-col gap-3 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault()
          setSubmittedSearch(searchInput.trim())
          setPage(0)
          setReloadKey((value) => value + 1)
        }}
      >
        <label className="sr-only" htmlFor="item-search">Поиск предметов</label>
        <input
          id="item-search"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Поиск по названию или slug"
          maxLength={100}
          className="min-w-0 flex-1 rounded-lg border border-stone-700 bg-stone-900 px-4 py-2 text-sm"
        />
        <select
          aria-label="Фильтр по гостинице"
          value={hotelFilter}
          onChange={(event) => {
            setHotelFilter(event.target.value)
            setCollectionFilter('')
            setPage(0)
          }}
          className="rounded-lg border border-stone-700 bg-stone-900 px-4 py-2 text-sm"
        >
          <option value="">Все гостиницы</option>
          {sites.map((site) => (
            <option key={site.hotel_name} value={site.hotel_name}>{site.hotel_name}</option>
          ))}
        </select>
        <select
          aria-label="Фильтр по коллекции"
          value={collectionFilter}
          onChange={(event) => {
            setCollectionFilter(event.target.value)
            setPage(0)
          }}
          className="rounded-lg border border-stone-700 bg-stone-900 px-4 py-2 text-sm"
        >
          <option value="">Все коллекции</option>
          {collections
            .filter((collection) => !hotelFilter || collection.hotel_name === hotelFilter)
            .map((collection) => (
            <option key={collection.id} value={collection.id}>{collection.name}</option>
          ))}
        </select>
        <select
          aria-label="Фильтр по публикации"
          value={statusFilter}
          onChange={(event) => {
            setStatusFilter(event.target.value)
            setPage(0)
          }}
          className="rounded-lg border border-stone-700 bg-stone-900 px-4 py-2 text-sm"
        >
          <option value="">Все статусы</option>
          <option value="active">Опубликованы</option>
          <option value="inactive">Скрыты</option>
        </select>
        <button type="submit" className="rounded-lg border border-stone-700 px-4 py-2 text-sm">Найти</button>
      </form>

      {error && (
        <p role="alert" aria-live="polite" className="mt-6 text-sm text-red-400">
          {error}
        </p>
      )}

      <div className="mt-8 overflow-hidden rounded-xl border border-stone-800">
        <div className="divide-y divide-stone-800">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex flex-col items-stretch justify-between gap-4 bg-stone-900/40 px-5 py-4 sm:flex-row sm:items-center sm:gap-6"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <h2 className="truncate font-medium">
                    {item.name}
                  </h2>

                  <span
                    className={[
                      'rounded-full px-2.5 py-1 text-xs',
                      item.is_active
                        ? 'bg-emerald-950 text-emerald-400'
                        : 'bg-stone-800 text-stone-500',
                    ].join(' ')}
                  >
                    {item.is_active
                      ? 'Опубликован'
                      : 'Скрыт'}
                  </span>

                  <span className="rounded-full bg-stone-800 px-2.5 py-1 text-xs text-stone-400">
                    {item.hotel_name}
                  </span>
                </div>

                <p className="mt-1 text-sm text-stone-500">
                  /i/{item.public_id}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 sm:shrink-0">
                <a
                  href={`${sites.find((site) => site.hotel_name === item.hotel_name)?.base_url ?? ''}/i/${item.public_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg border border-stone-700 px-3 py-2 text-sm text-stone-300 hover:border-stone-500"
                >
                  Открыть
                </a>

                <Link
                  to={`/admin/items/${item.id}`}
                  className="rounded-lg border border-stone-700 px-3 py-2 text-sm text-stone-300 hover:border-stone-500"
                >
                  Редактировать
                </Link>

                <button
                  type="button"
                  disabled={updatingId === item.id}
                  onClick={() =>
                    handleToggleActive(item)
                  }
                  className="rounded-lg border border-stone-700 px-3 py-2 text-sm text-stone-300 transition hover:border-stone-500 disabled:opacity-50"
                >
                  {updatingId === item.id
                    ? 'Сохранение...'
                    : item.is_active
                      ? 'Скрыть'
                      : 'Показать'}
                </button>
              </div>
            </div>
          ))}

          {items.length === 0 && (
            <div className="px-5 py-12 text-center text-stone-500">
              Предметов пока нет.
            </div>
          )}
        </div>
      </div>

      <div className="mt-5 flex items-center justify-between text-sm text-stone-400">
        <button
          type="button"
          disabled={page === 0}
          onClick={() => setPage((value) => Math.max(0, value - 1))}
          className="rounded-lg border border-stone-700 px-3 py-2 disabled:opacity-40"
        >
          Назад
        </button>
        <span>Страница {page + 1}</span>
        <button
          type="button"
          disabled={items.length < PAGE_SIZE}
          onClick={() => setPage((value) => value + 1)}
          className="rounded-lg border border-stone-700 px-3 py-2 disabled:opacity-40"
        >
          Далее
        </button>
      </div>
    </div>
  )
}

export default AdminItemsPage