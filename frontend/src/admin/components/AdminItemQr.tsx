import {
  useState,
} from 'react'

import {
  useNavigate,
} from 'react-router'

import {
  getAdminItemQrBlob,
} from '../api/qr'


interface AdminItemQrProps {
  itemId: number
  slug: string
  publicId: string
  hasUnsavedChanges: boolean
}


function AdminItemQr({
  itemId,
  slug,
  publicId,
  hasUnsavedChanges,
}: AdminItemQrProps) {
  const navigate = useNavigate()

  const [isDownloading, setIsDownloading] =
    useState(false)

  const [isPrinting, setIsPrinting] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)


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
      'Не удалось получить QR-код.',
    )
  }


  async function handleDownload() {
    setError(null)
    setIsDownloading(true)

    if (hasUnsavedChanges) {
      return
    }

    try {
      const blob =
        await getAdminItemQrBlob(itemId)

      const objectUrl =
        URL.createObjectURL(blob)

      const link =
        document.createElement('a')

      link.href = objectUrl
      link.download =
        `${slug}-qr.png`

      document.body.appendChild(link)

      link.click()
      link.remove()

      window.setTimeout(() => {
        URL.revokeObjectURL(objectUrl)
      }, 1000)
    } catch (error) {
      handleRequestError(error)
    } finally {
      setIsDownloading(false)
    }
  }


  async function handlePrint() {
    setError(null)

    /*
     * Окно открываем ДО await.
     * Иначе браузер может решить,
     * что это уже не пользовательский клик,
     * и заблокировать popup.
     */

    if (hasUnsavedChanges) {
      return
    }

    const printWindow =
      window.open(
        '',
        '_blank',
        'width=800,height=900',
      )

    if (!printWindow) {
      setError(
        'Браузер заблокировал окно печати.',
      )

      return
    }

    setIsPrinting(true)

    printWindow.document.title =
      `QR ${slug}`

    printWindow.document.body.textContent =
      'Подготовка QR-кода...'

    try {
      const blob =
        await getAdminItemQrBlob(itemId)

      const objectUrl =
        URL.createObjectURL(blob)

      const document =
        printWindow.document

      document.body.replaceChildren()

      document.body.style.margin = '0'
      document.body.style.padding = '24px'
      document.body.style.display = 'flex'
      document.body.style.justifyContent =
        'center'
      document.body.style.alignItems =
        'flex-start'
      document.body.style.background =
        'white'

      const image =
        document.createElement('img')

      image.src = objectUrl
      image.alt = `QR ${slug}`

      image.style.display = 'block'
      image.style.maxWidth = '100%'
      image.style.height = 'auto'

      image.onload = () => {
        printWindow.focus()
        printWindow.print()
      }

      document.body.appendChild(image)

      printWindow.onafterprint = () => {
        URL.revokeObjectURL(objectUrl)
        printWindow.close()
      }

      /*
       * Страховка на случай браузера,
       * который не вызовет onafterprint.
       */
      window.setTimeout(() => {
        URL.revokeObjectURL(objectUrl)
      }, 60_000)
    } catch (error) {
      printWindow.close()
      handleRequestError(error)
    } finally {
      setIsPrinting(false)
    }
  }


  return (
    <section className="rounded-xl border border-stone-800 bg-stone-900/40 p-6">
      <div className="flex flex-wrap items-center justify-between gap-6">
        <div>
          <h2 className="text-lg font-medium">
            QR-код
          </h2>

          <p className="mt-2 text-sm text-stone-500">
            Публичная страница:
          </p>

          <p className="mt-1 font-mono text-sm text-stone-400">
            /i/{publicId}
          </p>
          {hasUnsavedChanges && (
              <p className="mt-4 rounded-lg border border-amber-900 bg-amber-950/30 px-4 py-3 text-sm text-amber-400">
                Есть несохранённые изменения гостиницы, названия или slug.
                Сохраните предмет перед скачиванием или печатью QR:
                смена гостиницы меняет домен публичной ссылки.
              </p>
            )}
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={
              hasUnsavedChanges ||
              isDownloading ||
              isPrinting
            }
            onClick={handleDownload}
            className="rounded-lg border border-stone-700 px-4 py-2 text-sm text-stone-300 transition hover:border-stone-500 disabled:opacity-50"
          >
            {isDownloading
              ? 'Скачивание...'
              : 'Скачать QR'}
          </button>

          <button
            type="button"
            disabled={
              hasUnsavedChanges ||
              isDownloading ||
              isPrinting
            }
            onClick={handlePrint}
            className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium transition hover:bg-amber-600 disabled:opacity-50"
          >
            {isPrinting
              ? 'Подготовка...'
              : 'Распечатать'}
          </button>
        </div>
      </div>

      {error && (
        <p className="mt-5 rounded-lg border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
    </section>
  )
}


export default AdminItemQr