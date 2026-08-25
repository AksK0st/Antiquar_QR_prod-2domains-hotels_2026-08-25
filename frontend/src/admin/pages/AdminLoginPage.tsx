import {
  type FormEvent,
  useState,
} from 'react'

import { useNavigate } from 'react-router'

import { loginAdmin } from '../api/auth'
import { useSite } from '../../site/SiteContext'


function AdminLoginPage() {
  const navigate = useNavigate()
  const { hotelName } = useSite()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const [error, setError] = useState<string | null>(
    null,
  )

  const [isSubmitting, setIsSubmitting] =
    useState(false)

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setError(null)
    setIsSubmitting(true)

    try {
      await loginAdmin(
        username.trim(),
        password,
      )

      navigate(
        '/admin',
        {
          replace: true,
        },
      )
    } catch (error) {
      if (
        error instanceof Error &&
        error.message === 'INVALID_CREDENTIALS'
      ) {
        setError(
          'Неверное имя пользователя или пароль',
        )
      } else if (error instanceof Error && error.message === 'RATE_LIMITED') {
        setError('Слишком много попыток входа. Подождите несколько минут и повторите.')
      } else {
        setError('Не удалось выполнить вход. Попробуйте ещё раз.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen bg-stone-950 text-stone-100">
      <div className="mx-auto flex min-h-screen max-w-md items-center px-6">
        <div className="w-full">
          <div className="mb-10">
            <p className="mb-3 text-xs uppercase tracking-[0.25em] text-amber-500">
              Отель «{hotelName}»
            </p>

            <h1 className="text-3xl font-semibold">
              Управление каталогом
            </h1>

            <p className="mt-3 text-sm text-stone-400">
              Войдите в административную панель.
            </p>
          </div>

          <form
            aria-describedby={error ? 'admin-login-error' : undefined}
            onSubmit={handleSubmit}
            className="space-y-5"
          >
            <div>
              <label
                htmlFor="username"
                className="mb-2 block text-sm text-stone-300"
              >
                Логин
              </label>

              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(event) =>
                  setUsername(event.target.value)
                }
                required
                disabled={isSubmitting}
                className="w-full rounded-lg border border-stone-700 bg-stone-900 px-4 py-3 outline-none transition focus:border-amber-600"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-2 block text-sm text-stone-300"
              >
                Пароль
              </label>

              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                required
                disabled={isSubmitting}
                className="w-full rounded-lg border border-stone-700 bg-stone-900 px-4 py-3 outline-none transition focus:border-amber-600"
              />
            </div>

            {error && (
              <p id="admin-login-error" role="alert" aria-live="polite" className="text-sm text-red-400">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-lg bg-amber-700 px-4 py-3 font-medium transition hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting
                ? 'Вход...'
                : 'Войти'}
            </button>
          </form>
        </div>
      </div>
    </main>
  )
}

export default AdminLoginPage