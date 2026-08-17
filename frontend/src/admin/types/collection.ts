export interface AdminCollection {
  id: number
  version: number
  created_at: string
  updated_at: string
  slug: string
  name: string
  description: string | null
  location: string | null
}
