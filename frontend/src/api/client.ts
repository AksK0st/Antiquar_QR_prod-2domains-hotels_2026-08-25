export class ApiError extends Error {
  status: number
  detail: string | null
  requestId: string | null

  constructor(
    status: number,
    message: string,
    detail: string | null = null,
    requestId: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.requestId = requestId
  }
}

function combineSignal(
  external?: AbortSignal,
  timeoutMs = 15_000,
): { signal: AbortSignal; cleanup: () => void } {
  const controller = new AbortController()
  const timeout = window.setTimeout(
    () => controller.abort(new DOMException('Request timed out', 'TimeoutError')),
    timeoutMs,
  )

  const onAbort = () => controller.abort(external?.reason)
  if (external) {
    if (external.aborted) {
      onAbort()
    } else {
      external.addEventListener('abort', onAbort, { once: true })
    }
  }

  return {
    signal: controller.signal,
    cleanup: () => {
      window.clearTimeout(timeout)
      external?.removeEventListener('abort', onAbort)
    },
  }
}

function errorDetailToString(value: unknown): string | null {
  if (typeof value === 'string') {
    return value
  }

  if (Array.isArray(value)) {
    const messages = value
      .map((entry) => {
        if (typeof entry === 'string') return entry
        if (entry && typeof entry === 'object' && 'msg' in entry) {
          const message = (entry as { msg?: unknown }).msg
          return typeof message === 'string' ? message : null
        }
        return null
      })
      .filter((message): message is string => Boolean(message))

    return messages.length > 0 ? messages.join('; ') : null
  }

  if (value && typeof value === 'object' && 'msg' in value) {
    const message = (value as { msg?: unknown }).msg
    return typeof message === 'string' ? message : null
  }

  return null
}

async function parseError(response: Response): Promise<ApiError> {
  let detail: string | null = null
  try {
    const payload = await response.json() as { detail?: unknown }
    detail = errorDetailToString(payload.detail)
  } catch {
    // Error bodies are not guaranteed to be JSON.
  }

  return new ApiError(
    response.status,
    detail ?? `HTTP ${response.status}`,
    detail,
    response.headers.get('x-request-id'),
  )
}

export async function apiFetch<T>(
  url: string,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<T> {
  const combined = combineSignal(signal)
  try {
    const response = await fetch(url, {
      ...init,
      credentials: init.credentials ?? 'same-origin',
      signal: combined.signal,
    })
    if (!response.ok) {
      throw await parseError(response)
    }
    if (response.status === 204) {
      return undefined as T
    }
    return await response.json() as T
  } finally {
    combined.cleanup()
  }
}

export async function apiBlob(
  url: string,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<Blob> {
  const combined = combineSignal(signal, 30_000)
  try {
    const response = await fetch(url, {
      ...init,
      credentials: init.credentials ?? 'same-origin',
      signal: combined.signal,
    })
    if (!response.ok) {
      throw await parseError(response)
    }
    return await response.blob()
  } finally {
    combined.cleanup()
  }
}

export function jsonRequest(method: string, data?: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: data === undefined ? undefined : JSON.stringify(data),
  }
}
