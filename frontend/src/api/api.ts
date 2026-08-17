import { apiFetch } from './client'
import type { Item, ItemSummary } from '../types/item'
import type { Collection } from '../types/collection'

const API_URL = '/api/public'

export function getItems(signal?: AbortSignal): Promise<ItemSummary[]> {
  return apiFetch<ItemSummary[]>(`${API_URL}/items/`, {}, signal)
}

export function getItemBySlug(slug: string, signal?: AbortSignal): Promise<Item> {
  return apiFetch<Item>(`${API_URL}/items/${encodeURIComponent(slug)}`, {}, signal)
}

export function getItemByPublicId(publicId: string, signal?: AbortSignal): Promise<Item> {
  return apiFetch<Item>(
    `${API_URL}/items/by-public-id/${encodeURIComponent(publicId)}`,
    {},
    signal,
  )
}

export function getItemImageUrl(slug: string): string {
  return `${API_URL}/images/${encodeURIComponent(slug)}`
}

export function getCollections(signal?: AbortSignal): Promise<Collection[]> {
  return apiFetch<Collection[]>(`${API_URL}/collections/`, {}, signal)
}

export function getItemImageByIdUrl(
  slug: string,
  imageId: number,
  contentVersion: number,
): string {
  return `${API_URL}/images/${encodeURIComponent(slug)}/${imageId}?v=${contentVersion}`
}
