import { env } from '@/lib/env'
import { supabase } from '@/lib/supabase'

const TIMEOUT_MS = 30_000

export class ApiError extends Error {
  readonly status: number
  readonly isNetworkError: boolean

  constructor(message: string, status: number, isNetworkError: boolean) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.isNetworkError = isNetworkError
  }
}

export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS)

  let response: Response
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(session ? { Authorization: `Bearer ${session.access_token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Network error'
    throw new ApiError(message, 0, true)
  } finally {
    clearTimeout(timeout)
  }

  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText)
    throw new ApiError(message || response.statusText, response.status, false)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
