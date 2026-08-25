import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

import { getCurrentSite } from '../api/api'


interface SiteContextValue {
  hotelName: string
}

const DEFAULT_HOTEL_NAME = 'Галерея'

const SiteContext = createContext<SiteContextValue>({
  hotelName: DEFAULT_HOTEL_NAME,
})


function setMetaContent(selector: string, content: string) {
  const element = document.querySelector<HTMLMetaElement>(selector)
  if (element) {
    element.content = content
  }
}


export function SiteProvider({ children }: { children: ReactNode }) {
  const [hotelName, setHotelName] = useState(DEFAULT_HOTEL_NAME)

  useEffect(() => {
    const controller = new AbortController()

    getCurrentSite(controller.signal)
      .then((site) => setHotelName(site.hotel_name))
      .catch(() => {
        // Keep the safe local/default title. API pages will show their own error if needed.
      })

    return () => controller.abort()
  }, [])

  useEffect(() => {
    const title = `Исторические предметы — Отель «${hotelName}»`
    const description = `Каталог исторических предметов и коллекций отеля «${hotelName}».`
    const isItemPage = /^\/(?:items|i)\//.test(window.location.pathname)

    if (!isItemPage) {
      document.title = title
      setMetaContent('meta[name="description"]', description)
    }
    setMetaContent('meta[property="og:title"]', title)
    setMetaContent('meta[property="og:description"]', description)
    setMetaContent('meta[property="og:url"]', `${window.location.origin}/`)
    setMetaContent('meta[property="og:image"]', `${window.location.origin}/og-image.png`)
    setMetaContent('meta[property="og:image:alt"]', title)
  }, [hotelName])

  return (
    <SiteContext.Provider value={{ hotelName }}>
      {children}
    </SiteContext.Provider>
  )
}


export function useSite(): SiteContextValue {
  return useContext(SiteContext)
}
