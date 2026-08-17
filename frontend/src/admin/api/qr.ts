import { ApiError, apiBlob } from '../../api/client'
const getQrUrl = (itemId: number) => `/api/admin/items/${itemId}/qr`
export async function getAdminItemQrBlob(itemId: number): Promise<Blob> {
  try { return await apiBlob(getQrUrl(itemId)) }
  catch (error) {
    if (error instanceof ApiError && error.status === 401) throw new Error('UNAUTHORIZED')
    if (error instanceof ApiError && error.status === 404) throw new Error('NOT_FOUND')
    throw error
  }
}
