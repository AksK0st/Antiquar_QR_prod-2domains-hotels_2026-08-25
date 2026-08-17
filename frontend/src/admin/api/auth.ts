import { ApiError, apiFetch, jsonRequest } from '../../api/client'

const ADMIN_AUTH_URL = '/api/admin/auth'

export interface AdminUser { id: number; username: string }
export interface AdminLoginResponse { authenticated: boolean; username: string }

export async function loginAdmin(username: string, password: string): Promise<AdminLoginResponse> {
  try {
    return await apiFetch<AdminLoginResponse>(
      `${ADMIN_AUTH_URL}/login`,
      jsonRequest('POST', { username, password }),
    )
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) throw new Error('INVALID_CREDENTIALS')
    if (error instanceof ApiError && error.status === 429) throw new Error('RATE_LIMITED')
    throw error
  }
}

export async function getCurrentAdmin(signal?: AbortSignal): Promise<AdminUser> {
  try {
    return await apiFetch<AdminUser>(`${ADMIN_AUTH_URL}/me`, {}, signal)
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) throw new Error('UNAUTHORIZED')
    throw error
  }
}

export async function logoutAdmin(): Promise<void> {
  await apiFetch<void>(`${ADMIN_AUTH_URL}/logout`, { method: 'POST' })
}
