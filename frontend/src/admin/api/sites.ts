import { ApiError, apiFetch } from '../../api/client'

export interface AdminSite {
  hotel_name: string
  base_url: string
}

interface AdminSitesResponse {
  sites: AdminSite[]
}

export async function getAdminSites(signal?: AbortSignal): Promise<AdminSite[]> {
  try {
    const response = await apiFetch<AdminSitesResponse>('/api/admin/sites/', {}, signal)
    return response.sites
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) throw new Error('UNAUTHORIZED')
    throw error
  }
}
