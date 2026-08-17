import { useState } from 'react'

import ItemCard from './ItemCard'

import type { Collection } from '../types/collection'
import type { ItemSummary } from '../types/item'


interface CollectionSectionProps {
  collection: Collection
  items: ItemSummary[]
}


function CollectionSection({
  collection,
  items,
}: CollectionSectionProps) {
  const [isOpen, setIsOpen] = useState(true)


  return (
    <section className="border-b border-[#c9beae]">

      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="
          group
          flex
          w-full
          items-center
          justify-between
          gap-6
          py-7
          text-left
        "
      >

        <div>

          <div className="
            text-sm
            uppercase
            tracking-[0.18em]
            text-[#896943]
          ">
            Коллекция
          </div>


          <h2 className="
            font-display
            mt-2
            text-3xl
            leading-tight
            text-[#25211c]
            sm:text-4xl
          ">
            {collection.name}
          </h2>


          {collection.location && (
            <p className="mt-2 text-base text-[#756e65]">
              {collection.location}
            </p>
          )}

        </div>


        <div className="flex shrink-0 items-center gap-6">

          <span className="hidden text-base text-[#756e65] sm:block">
            {items.length}{' '}
            {items.length === 1 ? 'предмет' : 'предметов'}
          </span>


          <span
            className={`
              flex
              h-11
              w-11
              items-center
              justify-center
              rounded-full
              border
              border-[#aa987f]
              text-xl
              text-[#765f46]
              transition
              duration-300
              group-hover:border-[#765f46]
              ${isOpen ? 'rotate-180' : ''}
            `}
          >
            ↓
          </span>

        </div>

      </button>


      <div
        className={`
          grid
          transition-all
          duration-500
          ease-in-out
          ${
            isOpen
              ? 'grid-rows-[1fr] opacity-100'
              : 'grid-rows-[0fr] opacity-0'
          }
        `}
      >

        <div className="overflow-hidden">

          {collection.description && (
            <p className="
              mb-10
              max-w-2xl
              text-lg
              leading-8
              text-[#625b52]
            ">
              {collection.description}
            </p>
          )}


          <div className="
            grid
            gap-x-10
            gap-y-16
            pb-16
            md:grid-cols-2
          ">

            {items.map((item) => (
              <ItemCard
                key={item.id}
                item={item}
              />
            ))}

          </div>

        </div>

      </div>

    </section>
  )
}

export default CollectionSection