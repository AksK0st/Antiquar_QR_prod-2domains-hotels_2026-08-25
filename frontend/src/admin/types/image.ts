export interface AdminItemImage {
  id: number
  item_id: number
  original_filename: string | null
  content_type: string | null
  size: number | null
  width: number | null
  height: number | null
  content_version: number
  sort_order: number
  is_primary: boolean
}
