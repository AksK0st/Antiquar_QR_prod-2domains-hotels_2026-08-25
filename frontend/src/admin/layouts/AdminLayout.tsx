import {
  useEffect,
  useState,
} from 'react'

import {
  NavLink,
  Outlet,
  useNavigate,
} from 'react-router'

import {
  getCurrentAdmin,
  logoutAdmin,
  type AdminUser,
} from '../api/auth'


function AdminLayout() {
  const navigate = useNavigate()

  const [admin, setAdmin] =
    useState<AdminUser | null>(null)

  const [isLoading, setIsLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const [isLoggingOut, setIsLoggingOut] =
    useState(false)

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    async function checkAuthentication() {
      try {
        const currentAdmin =
          await getCurrentAdmin(controller.signal)

        if (!cancelled) {
          setAdmin(currentAdmin)
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
          'Не удалось проверить авторизацию.',
        )
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void checkAuthentication()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [navigate])

  async function handleLogout() {
    setIsLoggingOut(true)
    setError(null)

    try {
      await logoutAdmin()

      navigate(
        '/admin/login',
        {
          replace: true,
        },
      )
    } catch {
      setError(
        'Не удалось выйти из системы.',
      )

      setIsLoggingOut(false)
    }
  }

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-stone-950 text-stone-400">
        Проверка авторизации...
      </main>
    )
  }

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-stone-950 px-6">
        <div className="text-center">
          <p className="text-red-400">
            {error}
          </p>

          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-5 rounded-lg border border-stone-700 px-4 py-2 text-sm text-stone-200 hover:border-stone-500"
          >
            Повторить
          </button>
        </div>
      </main>
    )
  }

  if (!admin) {
    return null
  }

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100">
      <header className="border-b border-stone-800">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-4 px-4 py-5 sm:flex-row sm:items-center sm:px-6">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-amber-600">
              Отель «Галерея»
            </p>

            <p className="mt-1 font-medium">
              Административная панель
            </p>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-sm text-stone-400">
              {admin.username}
            </span>

            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="rounded-lg border border-stone-700 px-4 py-2 text-sm transition hover:border-stone-500 disabled:opacity-50"
            >
              {isLoggingOut
                ? 'Выход...'
                : 'Выйти'}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-10 lg:py-8">
        <aside className="overflow-x-auto">
          <nav className="flex min-w-max gap-2 lg:block lg:min-w-0 lg:space-y-2">
            <NavLink
              to="/admin"
              end
              className={({ isActive }) =>
                [
                  'block whitespace-nowrap rounded-lg px-4 py-3 text-sm transition',
                  isActive
                    ? 'bg-stone-800 text-amber-500'
                    : 'text-stone-400 hover:bg-stone-900 hover:text-stone-200',
                ].join(' ')
              }
            >
              Обзор
            </NavLink>

            <NavLink
              to="/admin/items"
              className={({ isActive }) =>
                [
                  'block whitespace-nowrap rounded-lg px-4 py-3 text-sm transition',
                  isActive
                    ? 'bg-stone-800 text-amber-500'
                    : 'text-stone-400 hover:bg-stone-900 hover:text-stone-200',
                ].join(' ')
              }
            >
              Предметы
            </NavLink>

            <NavLink
              to="/admin/collections"
              className={({ isActive }) =>
                [
                  'block whitespace-nowrap rounded-lg px-4 py-3 text-sm transition',
                  isActive
                    ? 'bg-stone-800 text-white'
                    : 'text-stone-400 hover:bg-stone-900 hover:text-stone-200',
                ].join(' ')
              }
            >
              Коллекции
            </NavLink>
          </nav>
        </aside>

        <main>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default AdminLayout