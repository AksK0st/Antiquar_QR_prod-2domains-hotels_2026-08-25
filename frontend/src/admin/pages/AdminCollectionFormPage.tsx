import {
  useEffect,
  useState,
  type FormEvent,
} from 'react'

import {
  Link,
  useNavigate,
  useParams,
} from 'react-router'

import {
  createAdminCollection,
  getAdminCollection,
  updateAdminCollection,
  type AdminCollectionPayload,
} from '../api/collections'


interface FormState {
  slug: string
  name: string
  description: string
  location: string
}


const EMPTY_FORM: FormState = {
  slug: '',
  name: '',
  description: '',
  location: '',
}


function emptyToNull(
  value: string,
): string | null {
  const trimmed = value.trim()

  return trimmed === ''
    ? null
    : trimmed
}


function AdminCollectionFormPage() {
  const navigate = useNavigate()

  const {
    collectionId,
  } = useParams()

  const parsedCollectionId =
    collectionId
      ? Number(collectionId)
      : null

  const isEditing =
    parsedCollectionId !== null

  const [form, setForm] =
    useState<FormState>(EMPTY_FORM)

  const [isLoading, setIsLoading] =
    useState(isEditing)

  const [isSaving, setIsSaving] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)
  const [collectionVersion, setCollectionVersion] = useState<number | null>(null)


  useEffect(() => {
    if (
      !isEditing ||
      parsedCollectionId === null
    ) {
      return
    }

    const controller = new AbortController()
    let cancelled = false

    async function loadCollection() {
      try {
        const collection =
          await getAdminCollection(
            parsedCollectionId,
            controller.signal,
          )

        if (cancelled) {
          return
        }

        setCollectionVersion(collection.version)
        setForm({
          slug: collection.slug,
          name: collection.name,
          description:
            collection.description ?? '',
          location:
            collection.location ?? '',
        })
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

        if (
          error instanceof Error &&
          error.message === 'NOT_FOUND'
        ) {
          setError(
            'Коллекция не найдена.',
          )

          return
        }

        setError(
          'Не удалось загрузить коллекцию.',
        )
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadCollection()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [
    isEditing,
    navigate,
    parsedCollectionId,
  ])


  function setField<
    K extends keyof FormState
  >(
    field: K,
    value: FormState[K],
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }))
  }


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setError(null)
    setIsSaving(true)

    const payload:
    AdminCollectionPayload = {
      slug: form.slug.trim(),
      name: form.name.trim(),

      description:
        emptyToNull(
          form.description,
        ),

      location:
        emptyToNull(
          form.location,
        ),
    }

    try {
      if (
        isEditing &&
        parsedCollectionId !== null
      ) {
        await updateAdminCollection(
          parsedCollectionId,
          payload,
          collectionVersion ?? 0,
        )
      } else {
        await createAdminCollection(
          payload,
        )
      }

      navigate(
        '/admin/collections',
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
        error.message === 'SLUG_CONFLICT'
      ) {
        setError(
          'Такой slug уже используется другой коллекцией.',
        )

        return
      }

      if (error instanceof Error && error.message === 'VERSION_CONFLICT') {
        setError('Коллекция уже изменена в другой вкладке. Перезагрузите страницу.')
      } else if (error instanceof Error && error.message === 'SLUG_CONFLICT') {
        setError('Такой slug уже используется другой коллекцией.')
      } else {
        setError('Не удалось сохранить коллекцию.')
      }
    } finally {
      setIsSaving(false)
    }
  }


  if (isLoading) {
    return (
      <p className="text-stone-400">
        Загрузка...
      </p>
    )
  }


  return (
    <div className="max-w-3xl">
      <div className="flex items-start justify-between gap-6">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-amber-600">
            Коллекции
          </p>

          <h1 className="mt-2 text-3xl font-semibold">
            {isEditing
              ? 'Редактирование коллекции'
              : 'Новая коллекция'}
          </h1>
        </div>

        <Link
          to="/admin/collections"
          className="rounded-lg border border-stone-700 px-4 py-2 text-sm text-stone-300 hover:border-stone-500"
        >
          Назад
        </Link>
      </div>

      {error && (
        <p className="mt-6 rounded-lg border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      <form
        onSubmit={handleSubmit}
        className="mt-8 space-y-8"
      >
        <section className="rounded-xl border border-stone-800 bg-stone-900/40 p-6">
          <div className="grid gap-5 md:grid-cols-2">
            <label>
              <span className="mb-2 block text-sm text-stone-400">
                Название
              </span>

              <input
                required
                value={form.name}
                onChange={(event) =>
                  setField(
                    'name',
                    event.target.value,
                  )
                }
                className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-amber-600"
              />
            </label>

            <label>
              <span className="mb-2 block text-sm text-stone-400">
                Slug
              </span>

              <input
                required
                value={form.slug}
                onChange={(event) =>
                  setField(
                    'slug',
                    event.target.value,
                  )
                }
                className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 font-mono text-sm outline-none focus:border-amber-600"
              />

              <span className="mt-2 block text-xs text-stone-600">
                Используется в публичной ссылке коллекции.
              </span>
            </label>
          </div>

          <label className="mt-5 block">
            <span className="mb-2 block text-sm text-stone-400">
              Описание
            </span>

            <textarea
              value={form.description}
              onChange={(event) =>
                setField(
                  'description',
                  event.target.value,
                )
              }
              rows={6}
              className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-amber-600"
            />
          </label>

          <label className="mt-5 block">
            <span className="mb-2 block text-sm text-stone-400">
              Местоположение
            </span>

            <input
              value={form.location}
              onChange={(event) =>
                setField(
                  'location',
                  event.target.value,
                )
              }
              className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-amber-600"
            />
          </label>
        </section>

        <div className="flex justify-end gap-3">
          <Link
            to="/admin/collections"
            className="rounded-lg border border-stone-700 px-5 py-3 text-sm text-stone-300 hover:border-stone-500"
          >
            Отмена
          </Link>

          <button
            type="submit"
            disabled={isSaving}
            className="rounded-lg bg-amber-700 px-5 py-3 text-sm font-medium transition hover:bg-amber-600 disabled:opacity-50"
          >
            {isSaving
              ? 'Сохранение...'
              : isEditing
                ? 'Сохранить'
                : 'Создать коллекцию'}
          </button>
        </div>
      </form>
    </div>
  )
}


export default AdminCollectionFormPage