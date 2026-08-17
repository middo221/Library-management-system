import axios, {
  AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios'

import { toApiError } from './errors'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from './tokens'
import type { TokenPair } from './types'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

/** Paths that must never trigger a refresh-and-retry — they *are* the auth flow. */
const AUTH_PATHS = ['/auth/login', '/auth/register', '/auth/refresh']

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean }

/** Raised when the session is gone for good; the app listens and redirects to login. */
export const SESSION_EXPIRED_EVENT = 'library:session-expired'

function announceSessionExpired(): void {
  clearTokens()
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT))
}

/**
 * A bare axios instance for the refresh call itself. Using the main client here would
 * recurse through its own 401 interceptor. Exported so tests can intercept it.
 */
export const refreshClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

/**
 * The in-flight refresh, shared by every request that hits a 401 at the same time.
 *
 * Three requests racing an expired token produce exactly one call to /auth/refresh: the
 * first creates the promise, the others await it, and all three then replay with the new
 * token.
 */
let refreshInFlight: Promise<string> | null = null

export function refreshAccessToken(): Promise<string> {
  if (refreshInFlight) return refreshInFlight

  const refresh = getRefreshToken()
  if (!refresh) {
    return Promise.reject(toApiError({ response: { status: 401, data: undefined } }))
  }

  refreshInFlight = refreshClient
    .post<TokenPair>('/auth/refresh', { refresh })
    .then(({ data }) => {
      setAccessToken(data.access)
      setRefreshToken(data.refresh)
      return data.access
    })
    .finally(() => {
      refreshInFlight = null
    })

  return refreshInFlight
}

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined
    const status = error.response?.status
    const isAuthPath = AUTH_PATHS.some((path) => config?.url?.startsWith(path))

    if (status !== 401 || !config || config._retried || isAuthPath) {
      return Promise.reject(toApiError(error))
    }

    config._retried = true

    try {
      const token = await refreshAccessToken()
      config.headers.Authorization = `Bearer ${token}`
      return await api.request(config)
    } catch {
      announceSessionExpired()
      return Promise.reject(toApiError(error))
    }
  },
)

/** Test seam: reset module state between cases. */
export function __resetRefreshState(): void {
  refreshInFlight = null
}
