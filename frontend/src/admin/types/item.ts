export interface AdminItem {
  id: number
  public_id: string
  hotel_name: string
  version: number
  created_at: string
  updated_at: string
  slug: string
  name: string
  short_description: string | null
  description: string | null
  period_from: number | null
  period_to: number | null
  period_text: string | null
  country: string | null
  creator: string | null
  material: string | null
  collection_id: number | null
  location: string | null
  attribution_notes: string | null
  sort_order: number
  is_active: boolean
}
