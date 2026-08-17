export interface ItemImage {
  id: number
  sort_order: number
  is_primary: boolean
  width: number | null
  height: number | null
  content_version: number
}

export interface ItemSummary {
  id: number
  public_id: string
  slug: string
  name: string
  short_description: string | null
  period_text: string | null
  collection_id: number | null
  sort_order: number
  primary_image: ItemImage | null
}

export interface Item extends ItemSummary {
  description: string | null
  period_from: number | null
  period_to: number | null
  country: string | null
  creator: string | null
  material: string | null
  attribution_notes: string | null
  is_active: boolean
  location: string | null
  images: ItemImage[]
}
