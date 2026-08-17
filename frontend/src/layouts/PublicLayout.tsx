import { Outlet } from 'react-router'
import Header from '../components/Header'


function PublicLayout() {
  return (
    <div className="min-h-screen bg-[#eee9df] text-stone-900">

      <Header />

      <Outlet />

      <footer className="mt-20 border-t border-stone-300">
        <div className="mx-auto max-w-7xl px-6 py-10 text-sm text-stone-500 lg:px-10">
          Отель "Галерея" · Каталог исторических предметов
        </div>
      </footer>

    </div>
  )
}

export default PublicLayout