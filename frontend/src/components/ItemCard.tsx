import { Link } from 'react-router'

import { getItemImageByIdUrl } from '../api/api'
import type { ItemSummary } from '../types/item'

interface ItemCardProps {
  item: ItemSummary
}

function ItemCard({ item }: ItemCardProps) {
  return (
    <Link
      to={`/i/${item.public_id}`}
      className="group block min-w-0"
    >
      <div className="relative overflow-hidden bg-[#d9d0c2]">
        <div className="aspect-[4/3] overflow-hidden">
          {item.primary_image ? (
            <img
              src={getItemImageByIdUrl(
                item.primary_image.id,
                item.primary_image.content_version,
              )}
              alt={item.name}
              width={item.primary_image.width ?? undefined}
              height={item.primary_image.height ?? undefined}
              loading="lazy"
              className="
                block
                h-full
                w-full
                object-contain
                object-center
              "
            />
          ) : (
            <div className="flex h-full items-center justify-center px-6 text-center text-sm text-[#756e65]">
              Фотография пока не добавлена
            </div>
          )}
        </div>

        {item.period_text && (
          <div
            className="
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
            "
          >
            {item.period_text}
          </div>
        )}
      </div>

      <div className="border-b border-[#cfc5b6] py-5">
        <div className="flex items-start justify-between gap-8">
          <div className="min-w-0">
            <h2
              className="
                font-display
                text-3xl
                leading-[1.05]
                tracking-tight
                text-[#25211c]
                transition
                group-hover:text-[#805c35]
              "
            >
              {item.name}
            </h2>

            {item.short_description && (
              <p className="mt-3 max-w-xl text-base leading-7 text-[#625b52]">
                {item.short_description}
              </p>
            )}
          </div>

          <div
            className="
              mt-1
              shrink-0
              text-xl
              text-[#9b764c]
              transition
              duration-300
              group-hover:translate-x-1
            "
          >
            →
          </div>
        </div>
      </div>
    </Link>
  )
}

export default ItemCard