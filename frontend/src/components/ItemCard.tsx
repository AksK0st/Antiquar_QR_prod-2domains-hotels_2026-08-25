import { Link } from 'react-router'

import { getItemImageUrl } from '../api/api'
import type { ItemSummary } from '../types/item'


interface ItemCardProps {
  item: ItemSummary
}


function ItemCard({ item }: ItemCardProps) {
  return (
    <Link
      to={`/items/${item.slug}`}
      className="group block"
    >

      <div className="relative overflow-hidden bg-[#d9d0c2]">

        <div className="aspect-[4/3] overflow-hidden">

          <img
            src={getItemImageUrl(item.slug)}
            alt={item.name}
            loading="lazy"
            className="
              h-full
              w-full
              object-cover
              transition
              duration-700
              ease-out
              group-hover:scale-[1.025]
            "
          />

        </div>


        {item.period_text && (
          <div className="
              absolute
              bottom-0
              left-0
              bg-[#24211d]
              px-4
              py-2.5
              text-xs
              uppercase
              tracking-[0.16em]
              text-[#d4b083]
            ">
            {item.period_text}
          </div>
        )}

      </div>


      <div className="border-b border-[#cfc5b6] py-5">

        <div className="flex items-start justify-between gap-8">

          <div>

            <h2 className="
              font-display
              text-3xl
              leading-[1.05]
              tracking-tight
              text-[#25211c]
              transition
              group-hover:text-[#805c35]
            ">
              {item.name}
            </h2>


            {item.short_description && (
              <p className="mt-3 max-w-xl text-base leading-7 text-[#625b52]">
                  {item.short_description}
              </p>
            )}

          </div>


          <div className="
            mt-1
            text-xl
            text-[#9b764c]
            transition
            duration-300
            group-hover:translate-x-1
          ">
            →
          </div>

        </div>

      </div>

    </Link>
  )
}

export default ItemCard