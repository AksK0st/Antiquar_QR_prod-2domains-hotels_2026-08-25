import {
  useEffect,
  useState,
} from 'react'

import {
  Link,
  useNavigate,
} from 'react-router'

import {
  getAdminCollections,
  deleteAdminCollection,
} from '../api/collections'

import type {
  AdminCollection,
} from '../types/collection'

const PAGE_SIZE = 50


function AdminCollectionsPage() {
  const navigate = useNavigate()

  const [collections, setCollections] =
    useState<AdminCollection[]>([])

  const [isLoading, setIsLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const [deletingId, setDeletingId] =
      useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [page, setPage] = useState(0)


  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    async function loadCollections() {
      try {
        const loaded =
          await getAdminCollections({ q: search.trim() || undefined, limit: PAGE_SIZE, offset: page * PAGE_SIZE, signal: controller.signal })

        if (!cancelled) {
          setCollections(loaded)
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
          'Не удалось загрузить коллекции.',
        )
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadCollections()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [navigate, reloadKey, page])


  async function handleDelete(
      collection: AdminCollection,
    ) {
      const confirmed = window.confirm(
        `Удалить коллекцию "${collection.name}"?`,
      )

      if (!confirmed) {
        return
      }

      setError(null)
      setDeletingId(collection.id)

      try {
        await deleteAdminCollection(
          collection.id,
        )

        setCollections((current) =>
          current.filter(
            (item) =>
              item.id !== collection.id,
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

        if (
          error instanceof Error &&
          error.message === 'COLLECTION_NOT_EMPTY'
        ) {
          setError(
            'Нельзя удалить коллекцию, пока в ней находятся предметы. Сначала перенесите или уберите их из коллекции.',
          )

          return
        }

        setError(
          'Не удалось удалить коллекцию.',
        )
      } finally {
        setDeletingId(null)
      }
    }


  if (isLoading) {
    return (
      <p className="text-stone-400">
        Загрузка коллекций...
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
            Коллекции
          </h1>

          <p className="mt-2 text-sm text-stone-500">
            Группы предметов, отображаемые
            в публичном каталоге.
          </p>
        </div>

        <Link
          to="/admin/collections/new"
          className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium transition hover:bg-amber-600"
        >
          Добавить коллекцию
        </Link>
      </div>

      <form
        className="mt-6 flex flex-col gap-3 sm:flex-row"
        onSubmit={(event) => { event.preventDefault(); setPage(0); setReloadKey((value) => value + 1) }}
      >
        <label className="sr-only" htmlFor="collection-search">Поиск коллекций</label>
        <input
          id="collection-search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Поиск по названию или slug"
          maxLength={100}
          className="min-w-0 flex-1 rounded-lg border border-stone-700 bg-stone-900 px-4 py-2 text-sm"
        />
        <button type="submit" className="rounded-lg border border-stone-700 px-4 py-2 text-sm">Найти</button>
      </form>

      {error && (
        <p className="mt-6 rounded-lg border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {collections.length === 0 ? (
        <div className="mt-8 rounded-xl border border-dashed border-stone-800 px-6 py-16 text-center">
          <p className="text-stone-400">
            Коллекций пока нет.
          </p>

          <p className="mt-2 text-sm text-stone-600">
            Предметы могут существовать
            и без коллекции.
          </p>
        </div>
      ) : (
        <div className="mt-8 overflow-hidden rounded-xl border border-stone-800">
          {collections.map(
            (collection) => (
              <div
                key={collection.id}
                className="flex items-center justify-between gap-6 border-b border-stone-800 bg-stone-900/40 px-5 py-4 last:border-b-0"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <p className="font-medium">
                      {collection.name}
                    </p>

                    <span className="rounded bg-stone-800 px-2 py-1 font-mono text-xs text-stone-500">
                      {collection.slug}
                    </span>
                  </div>

                  {collection.location && (
                    <p className="mt-2 text-sm text-stone-500">
                      {collection.location}
                    </p>
                  )}

                  {collection.description && (
                    <p className="mt-2 line-clamp-2 max-w-3xl text-sm text-stone-400">
                      {collection.description}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  <Link
                    to={`/admin/collections/${collection.id}`}
                    className="rounded-lg border border-stone-700 px-3 py-2 text-sm text-stone-300 transition hover:border-stone-500"
                  >
                    Редактировать
                  </Link>
                  <button
                      type="button"
                      disabled={deletingId !== null}
                      onClick={() =>
                        handleDelete(collection)
                      }
                      className="rounded-lg border border-red-900 px-3 py-2 text-sm text-red-400 transition hover:bg-red-950/40 disabled:opacity-50"
                    >
                      {deletingId === collection.id
                        ? 'Удаление...'
                        : 'Удалить'}
                    </button>
                </div>
              </div>
            ),
          )}
        </div>
      )}

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
          disabled={collections.length < PAGE_SIZE}
          onClick={() => setPage((value) => value + 1)}
          className="rounded-lg border border-stone-700 px-3 py-2 disabled:opacity-40"
        >
          Далее
        </button>
      </div>
    </div>
  )
}


export default AdminCollectionsPage