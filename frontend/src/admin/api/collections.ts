import { ApiError, apiFetch, jsonRequest } from '../../api/client'
import type { AdminCollection } from '../types/collection'

const ADMIN_COLLECTIONS_URL = '/api/admin/collections'
export interface AdminCollectionPayload {
  hotel_name: string
  slug: string
  name: string
  description: string | null
  location: string | null
}

function mapError(error: unknown): never {
  if (error instanceof ApiError) {
    if (error.status === 401) throw new Error('UNAUTHORIZED')
    if (error.status === 404) throw new Error('NOT_FOUND')
    if (error.status === 409) {
      if (error.detail?.includes('modified by another session')) throw new Error('VERSION_CONFLICT')
      if (error.detail?.includes('contains items')) throw new Error('COLLECTION_NOT_EMPTY')
      if (error.detail?.includes('cannot change hotel')) throw new Error('HOTEL_CHANGE_BLOCKED')
      throw new Error('SLUG_CONFLICT')
    }
  }
  throw error
}

export async function getAdminCollections(
  options: { q?: string; hotelName?: string; limit?: number; offset?: number; signal?: AbortSignal } = {},
): Promise<AdminCollection[]> {
  const params = new URLSearchParams()
  if (options.q) params.set('q', options.q)
  if (options.hotelName) params.set('hotel_name', options.hotelName)
  params.set('limit', String(options.limit ?? 100))
  params.set('offset', String(options.offset ?? 0))
  try { return await apiFetch<AdminCollection[]>(`${ADMIN_COLLECTIONS_URL}/?${params}`, {}, options.signal) }
  catch (error) { return mapError(error) }
}

export async function getAdminCollection(id: number, signal?: AbortSignal): Promise<AdminCollection> {
  try { return await apiFetch<AdminCollection>(`${ADMIN_COLLECTIONS_URL}/${id}`, {}, signal) }
  catch (error) { return mapError(error) }
}

export async function createAdminCollection(payload: AdminCollectionPayload): Promise<AdminCollection> {
  try { return await apiFetch<AdminCollection>(`${ADMIN_COLLECTIONS_URL}/`, jsonRequest('POST', payload)) }
  catch (error) { return mapError(error) }
}

export async function updateAdminCollection(
  id: number,
  payload: AdminCollectionPayload,
  expectedVersion: number,
): Promise<AdminCollection> {
  try {
    return await apiFetch<AdminCollection>(
      `${ADMIN_COLLECTIONS_URL}/${id}`,
      jsonRequest('PATCH', { ...payload, expected_version: expectedVersion }),
    )
  } catch (error) { return mapError(error) }
}

export async function deleteAdminCollection(id: number): Promise<void> {
  try { await apiFetch<void>(`${ADMIN_COLLECTIONS_URL}/${id}`, { method: 'DELETE' }) }
  catch (error) { return mapError(error) }
}
