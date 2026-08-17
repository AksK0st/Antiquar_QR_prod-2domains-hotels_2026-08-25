import { ApiError, apiFetch, jsonRequest } from '../../api/client'
import type { AdminItem } from '../types/item'

const ADMIN_ITEMS_URL = '/api/admin/items'

export interface AdminItemPayload {
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

function mapError(error: unknown): never {
  if (error instanceof ApiError) {
    if (error.status === 401) throw new Error('UNAUTHORIZED')
    if (error.status === 404) throw new Error('NOT_FOUND')
    if (error.status === 409) {
      if (error.detail?.includes('modified by another session')) throw new Error('VERSION_CONFLICT')
      throw new Error('SLUG_CONFLICT')
    }
  }
  throw error
}

export async function getAdminItems(
  options: {
    q?: string
    collectionId?: number
    isActive?: boolean
    limit?: number
    offset?: number
    signal?: AbortSignal
  } = {},
): Promise<AdminItem[]> {
  const params = new URLSearchParams()
  if (options.q) params.set('q', options.q)
  if (options.collectionId !== undefined) params.set('collection_id', String(options.collectionId))
  if (options.isActive !== undefined) params.set('is_active', String(options.isActive))
  params.set('limit', String(options.limit ?? 100))
  params.set('offset', String(options.offset ?? 0))
  try {
    return await apiFetch<AdminItem[]>(`${ADMIN_ITEMS_URL}/?${params}`, {}, options.signal)
  } catch (error) { return mapError(error) }
}

export async function setItemActive(item: AdminItem, isActive: boolean): Promise<AdminItem> {
  try {
    return await apiFetch<AdminItem>(
      `${ADMIN_ITEMS_URL}/${item.id}`,
      jsonRequest('PATCH', { is_active: isActive, expected_version: item.version }),
    )
  } catch (error) { return mapError(error) }
}

export async function getAdminItem(itemId: number, signal?: AbortSignal): Promise<AdminItem> {
  try { return await apiFetch<AdminItem>(`${ADMIN_ITEMS_URL}/${itemId}`, {}, signal) }
  catch (error) { return mapError(error) }
}

export async function createAdminItem(payload: AdminItemPayload): Promise<AdminItem> {
  try { return await apiFetch<AdminItem>(`${ADMIN_ITEMS_URL}/`, jsonRequest('POST', payload)) }
  catch (error) { return mapError(error) }
}

export async function updateAdminItem(
  itemId: number,
  payload: AdminItemPayload,
  expectedVersion: number,
): Promise<AdminItem> {
  try {
    return await apiFetch<AdminItem>(
      `${ADMIN_ITEMS_URL}/${itemId}`,
      jsonRequest('PATCH', { ...payload, expected_version: expectedVersion }),
    )
  } catch (error) { return mapError(error) }
}
