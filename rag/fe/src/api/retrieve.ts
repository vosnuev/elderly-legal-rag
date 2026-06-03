export const API_BASE_URL = import.meta.env.VITE_RAG_API_BASE_URL ?? 'http://127.0.0.1:8010'
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_RAG_API_TIMEOUT_MS ?? 1500)
const MOCK_FALLBACK_ENABLED = import.meta.env.VITE_RAG_ENABLE_MOCK_FALLBACK !== 'false'

let mockFallbackCount = 0

type RetrieveOptions<T> = {
  init?: RequestInit
  mock: () => T | Promise<T>
  path: string
  timeoutMs?: number
}

export async function retrieve<T>({
  init,
  mock,
  path,
  timeoutMs = DEFAULT_TIMEOUT_MS,
}: RetrieveOptions<T>): Promise<T> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...init?.headers,
      },
      ...init,
      signal: controller.signal,
    })

    if (!response.ok) {
      throw new Error(`RAG API request failed: ${response.status}`)
    }

    return response.json() as Promise<T>
  } catch (error) {
    if (!MOCK_FALLBACK_ENABLED) {
      throw error
    }

    mockFallbackCount += 1

    if (import.meta.env.DEV) {
      console.warn(`RAG API unavailable for ${path}. Serving mock data.`, error)
    }

    return mock()
  } finally {
    window.clearTimeout(timeoutId)
  }
}

export function resetMockFallbackState() {
  mockFallbackCount = 0
}

export function hasMockFallback() {
  return mockFallbackCount > 0
}
