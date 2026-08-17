import { Link } from 'react-router'


function Header() {
  return (
    <header className="
      border-b
      border-[#4a3b2b]
      bg-[#171512]
      text-[#f3ede1]
    ">

      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-10">

        <Link
          to="/"
          className="group"
        >
          <div className="font-display text-2xl leading-none tracking-tight">
            Отель "Галерея"
          </div>

          <div className="mt-2 text-xs uppercase tracking-[0.3em] text-[#c09a6d]">
            История в предметах
          </div>
        </Link>


        <Link
          to="/"
          className="
              border-b
              border-transparent
              pb-1
              text-base
              text-[#d4cbc0]
              transition
              hover:border-[#a67c4b]
              hover:text-[#f3ede1]
            "
        >
          Справочник
        </Link>

      </div>

    </header>
  )
}

export default Header