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
  createAdminItem,
  getAdminItem,
  updateAdminItem,
  type AdminItemPayload,
} from '../api/items'

import { getAdminCollections } from '../api/collections'
import { getAdminSites } from '../api/sites'
import { useSite } from '../../site/SiteContext'

import type { AdminCollection } from '../types/collection'

import AdminItemImages from '../components/AdminItemImages'

import AdminItemQr from '../components/AdminItemQr'


interface FormState {
  hotelName: string
  slug: string
  name: string
  shortDescription: string
  description: string
  periodFrom: string
  periodTo: string
  periodText: string
  country: string
  creator: string
  material: string
  collectionId: string
  location: string
  attributionNotes: string
  sortOrder: string
  isActive: boolean
}

interface SavedQrIdentity {
  hotelName: string
  name: string
  slug: string
}


const EMPTY_FORM: FormState = {
  hotelName: '',
  slug: '',
  name: '',
  shortDescription: '',
  description: '',
  periodFrom: '',
  periodTo: '',
  periodText: '',
  country: '',
  creator: '',
  material: '',
  collectionId: '',
  location: '',
  attributionNotes: '',
  sortOrder: '0',
  isActive: true,
}


function emptyToNull(
  value: string,
): string | null {
  const trimmed = value.trim()

  return trimmed === ''
    ? null
    : trimmed
}


function numberOrNull(
  value: string,
): number | null {
  if (value.trim() === '') {
    return null
  }

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}


function positiveId(value: string | undefined): number | null {
  if (!value || !/^\d+$/.test(value)) return null
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null
}


function AdminItemFormPage() {
  const navigate = useNavigate()
  const { itemId } = useParams()
  const { hotelName: currentHotelName } = useSite()

  const isEditing = itemId !== undefined
  const parsedItemId = positiveId(itemId)
  const hasInvalidItemId = isEditing && parsedItemId === null

  const [form, setForm] =
    useState<FormState>(EMPTY_FORM)

  const [collections, setCollections] =
    useState<AdminCollection[]>([])

  const [hotelNames, setHotelNames] = useState<string[]>([])

  const [isLoading, setIsLoading] =
    useState(true)

  const [isSaving, setIsSaving] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)
  const [loadFailed, setLoadFailed] = useState(false)
  const [itemVersion, setItemVersion] = useState<number | null>(null)
  const [publicId, setPublicId] = useState<string | null>(null)

  const [
      savedQrIdentity,
      setSavedQrIdentity,
    ] = useState<SavedQrIdentity | null>(null)


  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    if (hasInvalidItemId) {
      setError('Некорректный идентификатор предмета.')
      setLoadFailed(true)
      setIsLoading(false)
      return () => controller.abort()
    }

    async function loadData() {
      setIsLoading(true)
      setLoadFailed(false)
      setError(null)
      try {
        const [collectionsResult, sitesResult] = await Promise.all([
          getAdminCollections({ limit: 200, signal: controller.signal }),
          getAdminSites(controller.signal),
        ])

        if (cancelled) {
          return
        }

        setCollections(collectionsResult)
        const names = sitesResult.map((site) => site.hotel_name)
        setHotelNames(names)

        if (
          isEditing &&
          parsedItemId !== null
        ) {
          const item =
            await getAdminItem(parsedItemId, controller.signal)

          if (cancelled) {
            return
          }

          setSavedQrIdentity({
            hotelName: item.hotel_name,
            name: item.name,
            slug: item.slug,
          })
          setItemVersion(item.version)
          setPublicId(item.public_id)
          setForm({
            hotelName: item.hotel_name,
            slug: item.slug,
            name: item.name,
            shortDescription:
              item.short_description ?? '',
            description:
              item.description ?? '',
            periodFrom:
              item.period_from?.toString() ?? '',
            periodTo:
              item.period_to?.toString() ?? '',
            periodText:
              item.period_text ?? '',
            country:
              item.country ?? '',
            creator:
              item.creator ?? '',
            material:
              item.material ?? '',
            collectionId:
              item.collection_id?.toString() ?? '',
            location:
              item.location ?? '',
            attributionNotes:
              item.attribution_notes ?? '',
            sortOrder:
              item.sort_order.toString(),
            isActive:
              item.is_active,
          })
        } else {
          setForm((current) => ({
            ...current,
            hotelName: names.includes(currentHotelName)
              ? currentHotelName
              : names[0] ?? 'Галерея',
          }))
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

        setLoadFailed(true)
        setError(
          'Не удалось загрузить данные.',
        )
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadData()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [
    hasInvalidItemId,
    isEditing,
    navigate,
    parsedItemId,
    currentHotelName,
  ])


  function setField<K extends keyof FormState>(
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

    const payload: AdminItemPayload = {
      hotel_name: form.hotelName,
      slug: form.slug.trim(),
      name: form.name.trim(),

      short_description:
        emptyToNull(form.shortDescription),

      description:
        emptyToNull(form.description),

      period_from:
        numberOrNull(form.periodFrom),

      period_to:
        numberOrNull(form.periodTo),

      period_text:
        emptyToNull(form.periodText),

      country:
        emptyToNull(form.country),

      creator:
        emptyToNull(form.creator),

      material:
        emptyToNull(form.material),

      collection_id:
        numberOrNull(form.collectionId),

      location:
        emptyToNull(form.location),

      attribution_notes:
        emptyToNull(form.attributionNotes),

      sort_order:
        Number(form.sortOrder) || 0,

      is_active:
        form.isActive,
    }

    try {
      if (
        isEditing &&
        parsedItemId !== null
      ) {
        const updated =
          await updateAdminItem(
            parsedItemId,
            payload,
            itemVersion ?? 0,
          )

        setSavedQrIdentity({
          hotelName: updated.hotel_name,
          name: updated.name,
          slug: updated.slug,
        })
        setItemVersion(updated.version)
        setPublicId(updated.public_id)

        navigate(
          `/admin/items/${parsedItemId}`,
          {
            replace: true,
          },
        )
      } else {
        const created =
          await createAdminItem(payload)

        navigate(
          `/admin/items/${created.id}`,
          {
            replace: true,
          },
        )
      }
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

      if (error instanceof Error && error.message === 'VERSION_CONFLICT') {
        setError('Предмет уже изменён в другой вкладке. Перезагрузите страницу перед сохранением.')
      } else if (error instanceof Error && error.message === 'SLUG_CONFLICT') {
        setError('Такой slug уже используется другим предметом этой гостиницы.')
      } else {
        setError('Не удалось сохранить предмет.')
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

  if (loadFailed || (isEditing && (parsedItemId === null || itemVersion === null))) {
    return (
      <div className="max-w-4xl">
        <p role="alert" className="rounded-lg border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-400">
          {error ?? 'Не удалось открыть предмет.'}
        </p>
        <Link to="/admin/items" className="mt-5 inline-block text-sm text-stone-300 underline">
          Вернуться к предметам
        </Link>
      </div>
    )
  }

  const hasUnsavedQrChanges =
  savedQrIdentity !== null &&
  (
    form.hotelName.trim() !==
      savedQrIdentity.hotelName ||
    form.slug.trim() !==
      savedQrIdentity.slug ||
    form.name.trim() !==
      savedQrIdentity.name
  )


  return (
    <div className="max-w-4xl">
      <div className="flex items-start justify-between gap-6">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-amber-600">
            Предметы
          </p>

          <h1 className="mt-2 text-3xl font-semibold">
            {isEditing
              ? 'Редактирование предмета'
              : 'Новый предмет'}
          </h1>
        </div>

        <Link
          to="/admin/items"
          className="rounded-lg border border-stone-700 px-4 py-2 text-sm text-stone-300 hover:border-stone-500"
        >
          Назад
        </Link>
      </div>

      {error && (
        <p id="admin-item-form-error" role="alert" aria-live="polite" className="mt-6 rounded-lg border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
        {isEditing &&
          parsedItemId !== null && (
            <div className="mt-8 space-y-6">
              <AdminItemImages
                itemId={parsedItemId}
              />

              {savedQrIdentity && publicId && (
              <AdminItemQr
                itemId={parsedItemId}
                slug={savedQrIdentity.slug}
                publicId={publicId}
                hasUnsavedChanges={
                  hasUnsavedQrChanges
                }
              />
)}
            </div>
          )}

      <form
        id="admin-item-form"
        aria-describedby={error ? 'admin-item-form-error' : undefined}
        onSubmit={handleSubmit}
        className="mt-8 space-y-8"
      >
        <section className="rounded-xl border border-stone-800 bg-stone-900/40 p-6">
          <h2 className="text-lg font-medium">
            Основное
          </h2>

          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <label className="block">
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

            <label className="block">
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
                QR-код генерируется по сохранённой публичной ссылке предмета.
              </span>
            </label>
          </div>

          <label className="mt-5 block">
            <span className="mb-2 block text-sm text-stone-400">
              Краткое описание
            </span>

            <textarea
              value={form.shortDescription}
              onChange={(event) =>
                setField(
                  'shortDescription',
                  event.target.value,
                )
              }
              rows={3}
              className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-amber-600"
            />
          </label>

          <label className="mt-5 block">
            <span className="mb-2 block text-sm text-stone-400">
              Полное описание
            </span>

            <textarea
              value={form.description}
              onChange={(event) =>
                setField(
                  'description',
                  event.target.value,
                )
              }
              rows={8}
              className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-amber-600"
            />
          </label>
        </section>

        <section className="rounded-xl border border-stone-800 bg-stone-900/40 p-6">
          <h2 className="text-lg font-medium">
            Атрибуция
          </h2>

          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <TextField
              label="Страна"
              value={form.country}
              onChange={(value) =>
                setField('country', value)
              }
            />

            <TextField
              label="Автор / мастер"
              value={form.creator}
              onChange={(value) =>
                setField('creator', value)
              }
            />

            <TextField
              label="Материал"
              value={form.material}
              onChange={(value) =>
                setField('material', value)
              }
            />

            <TextField
              label="Местоположение"
              value={form.location}
              onChange={(value) =>
                setField('location', value)
              }
            />
          </div>

          <div className="mt-5 grid gap-5 md:grid-cols-3">
            <NumberField
              label="Год от"
              value={form.periodFrom}
              onChange={(value) =>
                setField('periodFrom', value)
              }
            />

            <NumberField
              label="Год до"
              value={form.periodTo}
              onChange={(value) =>
                setField('periodTo', value)
              }
            />

            <TextField
              label="Период текстом"
              value={form.periodText}
              onChange={(value) =>
                setField('periodText', value)
              }
            />
          </div>

          <label className="mt-5 block">
            <span className="mb-2 block text-sm text-stone-400">
              Примечание об атрибуции
            </span>

            <textarea
              value={form.attributionNotes}
              onChange={(event) =>
                setField(
                  'attributionNotes',
                  event.target.value,
                )
              }
              rows={4}
              className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-amber-600"
            />
          </label>
        </section>

        <section className="rounded-xl border border-stone-800 bg-stone-900/40 p-6">
          <h2 className="text-lg font-medium">
            Каталог
          </h2>

          <div className="mt-5 grid gap-5 md:grid-cols-3">
            <label>
              <span className="mb-2 block text-sm text-stone-400">
                Гостиница
              </span>

              <select
                required
                value={form.hotelName}
                onChange={(event) => {
                  const hotelName = event.target.value
                  const selectedCollection = collections.find(
                    (collection) => collection.id.toString() === form.collectionId,
                  )
                  setForm((current) => ({
                    ...current,
                    hotelName,
                    collectionId: selectedCollection?.hotel_name === hotelName
                      ? current.collectionId
                      : '',
                  }))
                }}
                className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-amber-600"
              >
                {hotelNames.map((hotelName) => (
                  <option key={hotelName} value={hotelName}>{hotelName}</option>
                ))}
              </select>
            </label>

            <label>
              <span className="mb-2 block text-sm text-stone-400">
                Коллекция
              </span>

              <select
                value={form.collectionId}
                onChange={(event) =>
                  setField(
                    'collectionId',
                    event.target.value,
                  )
                }
                className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-amber-600"
              >
                <option value="">
                  Без коллекции
                </option>

                {collections
                  .filter((collection) => collection.hotel_name === form.hotelName)
                  .map(
                  (collection) => (
                    <option
                      key={collection.id}
                      value={collection.id}
                    >
                      {collection.name}
                    </option>
                  ),
                )}
              </select>
            </label>

            <NumberField
              label="Порядок"
              value={form.sortOrder}
              onChange={(value) =>
                setField('sortOrder', value)
              }
            />
          </div>

          <label className="mt-6 flex items-center gap-3">
            <input
              type="checkbox"
              checked={form.isActive}
              onChange={(event) =>
                setField(
                  'isActive',
                  event.target.checked,
                )
              }
              className="h-4 w-4"
            />

            <span className="text-sm text-stone-300">
              Предмет опубликован
            </span>
          </label>
        </section>

        <div className="flex justify-end gap-3">
          <Link
            to="/admin/items"
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
                : 'Создать предмет'}
          </button>
        </div>
      </form>
    </div>
  )
}


interface FieldProps {
  label: string
  value: string
  onChange: (value: string) => void
}


function TextField({
  label,
  value,
  onChange,
}: FieldProps) {
  return (
    <label>
      <span className="mb-2 block text-sm text-stone-400">
        {label}
      </span>

      <input
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-amber-600"
      />
    </label>
  )
}


function NumberField({
  label,
  value,
  onChange,
}: FieldProps) {
  return (
    <label>
      <span className="mb-2 block text-sm text-stone-400">
        {label}
      </span>

      <input
        type="number"
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full rounded-lg border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-amber-600"
      />
    </label>
  )
}


export default AdminItemFormPage