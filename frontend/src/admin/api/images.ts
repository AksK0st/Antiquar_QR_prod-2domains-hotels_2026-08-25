import { ApiError, apiFetch, jsonRequest } from '../../api/client'
import type { AdminItemImage } from '../types/image'

const getImagesUrl = (itemId: number) => `/api/admin/items/${itemId}/images`
function mapError(error: unknown): never {
  if (error instanceof ApiError) {
    if (error.status === 401) throw new Error('UNAUTHORIZED')
    if (error.status === 413) throw new Error('IMAGE_TOO_LARGE')
    if (error.status === 415 || error.status === 422) throw new Error('INVALID_IMAGE')
  }
  throw error
}

export async function getAdminItemImages(itemId: number, signal?: AbortSignal): Promise<AdminItemImage[]> {
  try { return await apiFetch<AdminItemImage[]>(`${getImagesUrl(itemId)}/`, {}, signal) }
  catch (error) { return mapError(error) }
}
export const getAdminItemImageUrl = (itemId: number, imageId: number) => `${getImagesUrl(itemId)}/${imageId}/content`
export async function uploadAdminItemImage(itemId: number, file: File): Promise<AdminItemImage> {
  const formData = new FormData(); formData.append('file', file, file.name)
  try { return await apiFetch<AdminItemImage>(`${getImagesUrl(itemId)}/`, { method: 'POST', body: formData }) }
  catch (error) { return mapError(error) }
}
export async function setAdminItemPrimaryImage(itemId: number, imageId: number): Promise<AdminItemImage> {
  try { return await apiFetch<AdminItemImage>(`${getImagesUrl(itemId)}/${imageId}/primary`, { method: 'PATCH' }) }
  catch (error) { return mapError(error) }
}
export async function reorderAdminItemImages(itemId: number, imageIds: number[]): Promise<AdminItemImage[]> {
  try { return await apiFetch<AdminItemImage[]>(`${getImagesUrl(itemId)}/order`, jsonRequest('PATCH', { image_ids: imageIds })) }
  catch (error) { return mapError(error) }
}
export async function deleteAdminItemImage(itemId: number, imageId: number): Promise<void> {
  try { await apiFetch<void>(`${getImagesUrl(itemId)}/${imageId}`, { method: 'DELETE' }) }
  catch (error) { return mapError(error) }
}
