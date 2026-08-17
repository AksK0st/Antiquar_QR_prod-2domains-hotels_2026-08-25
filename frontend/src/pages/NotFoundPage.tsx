import { Link } from 'react-router'

function NotFoundPage() {
  return (
    <main className="flex min-h-[65vh] items-center justify-center bg-[#efe9de] px-6 text-[#25211c]">
      <div className="max-w-lg text-center">
        <p className="text-sm uppercase tracking-[0.2em] text-[#896943]">404</p>
        <h1 className="font-display mt-3 text-4xl">Страница не найдена</h1>
        <p className="mt-4 text-[#665f56]">Адрес мог измениться или страница больше не существует.</p>
        <Link to="/" className="mt-7 inline-block text-[#805c35] underline underline-offset-4">
          Вернуться в справочник
        </Link>
      </div>
    </main>
  )
}

export default NotFoundPage
