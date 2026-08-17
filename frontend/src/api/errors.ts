import type { ApiErrorEnvelope } from './types'

/**
 * The typed error every layer above the client sees.
 *
 * Unwrapping happens in exactly one place (the axios response interceptor), so no component
 * ever pokes at `error.response.data.error.message`.
 */
export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: Record<string, unknown>

  constructor(code: string, message: string, status: number, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }

  /** Field errors keyed by field name, for handing straight to react-hook-form. */
  get fieldErrors(): Record<string, string> {
    if (this.code !== 'VALIDATION_ERROR') return {}
    return Object.fromEntries(
      Object.entries(this.details).map(([field, value]) => [field, describe(value)]),
    )
  }
}

function describe(value: unknown): string {
  if (Array.isArray(value)) return value.map(describe).join(' ')
  if (value && typeof value === 'object') return Object.values(value).map(describe).join(' ')
  return String(value)
}

function isEnvelope(data: unknown): data is ApiErrorEnvelope {
  if (!data || typeof data !== 'object') return false
  const candidate = (data as ApiErrorEnvelope).error
  return Boolean(candidate) && typeof candidate.code === 'string'
}

/** Turn anything axios can throw into an ApiError. */
export function toApiError(error: unknown): ApiError {
  const axiosLike = error as {
    response?: { status?: number; data?: unknown }
    message?: string
    code?: string
  }

  const status = axiosLike?.response?.status ?? 0
  const data = axiosLike?.response?.data

  if (isEnvelope(data)) {
    return new ApiError(data.error.code, data.error.message, status, data.error.details ?? {})
  }

  if (status === 0) {
    return new ApiError(
      'NETWORK_ERROR',
      'The library service could not be reached. Check your connection and try again.',
      0,
    )
  }

  return new ApiError(
    'UNEXPECTED_ERROR',
    axiosLike?.message ?? 'Something went wrong. Please try again.',
    status,
  )
}

/** Message to show a person, given anything that was thrown. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Something went wrong. Please try again.'
}
