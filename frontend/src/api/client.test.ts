import MockAdapter from 'axios-mock-adapter'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  api,
  refreshAccessToken,
  refreshClient,
  SESSION_EXPIRED_EVENT,
  __resetRefreshState,
} from './client'
import { ApiError } from './errors'
import { getAccessToken, getRefreshToken, setAccessToken, setRefreshToken } from './tokens'

let mock: MockAdapter
let refreshMock: MockAdapter

function unauthorised() {
  return {
    error: {
      code: 'NOT_AUTHENTICATED',
      message: 'Authentication credentials were not provided.',
      details: {},
    },
  }
}

beforeEach(() => {
  mock = new MockAdapter(api)
  refreshMock = new MockAdapter(refreshClient)
  __resetRefreshState()
  setAccessToken('expired-access')
  setRefreshToken('valid-refresh')
})

afterEach(() => {
  mock.restore()
  refreshMock.restore()
  vi.restoreAllMocks()
})

describe('request interceptor', () => {
  it('attaches the in-memory access token', async () => {
    expect.assertions(1)
    mock.onGet('/books').reply((config) => {
      expect(config.headers?.Authorization).toBe('Bearer expired-access')
      return [200, { results: [] }]
    })

    await api.get('/books')
  })

  it('sends no Authorization header when signed out', async () => {
    expect.assertions(1)
    setAccessToken(null)
    mock.onGet('/books').reply((config) => {
      expect(config.headers?.Authorization).toBeUndefined()
      return [200, { results: [] }]
    })

    await api.get('/books')
  })
})

describe('401 handling', () => {
  it('refreshes exactly once with three requests in flight, then replays them all', async () => {
    let refreshCalls = 0
    let tokenIsFresh = false

    mock.onGet('/books').reply(() => (tokenIsFresh ? [200, { ok: true }] : [401, unauthorised()]))

    refreshMock.onPost('/auth/refresh').reply(() => {
      refreshCalls += 1
      tokenIsFresh = true
      return [200, { access: 'fresh-access', refresh: 'fresh-refresh' }]
    })

    const responses = await Promise.all([api.get('/books'), api.get('/books'), api.get('/books')])

    expect(refreshCalls).toBe(1)
    expect(responses.map((response) => response.data)).toEqual([
      { ok: true },
      { ok: true },
      { ok: true },
    ])
    expect(getAccessToken()).toBe('fresh-access')
    expect(getRefreshToken()).toBe('fresh-refresh')
  })

  it('retries a failed request only once', async () => {
    let attempts = 0
    mock.onGet('/books').reply(() => {
      attempts += 1
      return [401, unauthorised()]
    })
    refreshMock.onPost('/auth/refresh').reply(200, { access: 'a', refresh: 'b' })

    await expect(api.get('/books')).rejects.toBeInstanceOf(ApiError)
    expect(attempts).toBe(2)
  })

  it('never retries the auth endpoints', async () => {
    let attempts = 0
    mock.onPost('/auth/login').reply(() => {
      attempts += 1
      return [401, { error: { code: 'INVALID_CREDENTIALS', message: 'Nope.', details: {} } }]
    })

    await expect(api.post('/auth/login', {})).rejects.toMatchObject({
      code: 'INVALID_CREDENTIALS',
    })
    expect(attempts).toBe(1)
  })

  it('clears the session and announces expiry when the refresh is rejected', async () => {
    const listener = vi.fn()
    window.addEventListener(SESSION_EXPIRED_EVENT, listener)

    mock.onGet('/auth/me').reply(401, unauthorised())
    refreshMock.onPost('/auth/refresh').reply(401, {
      error: { code: 'INVALID_REFRESH_TOKEN', message: 'Already used.', details: {} },
    })

    await expect(api.get('/auth/me')).rejects.toBeInstanceOf(ApiError)

    expect(listener).toHaveBeenCalledTimes(1)
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()

    window.removeEventListener(SESSION_EXPIRED_EVENT, listener)
  })

  it('refuses to refresh with no stored refresh token', async () => {
    setRefreshToken(null)
    __resetRefreshState()

    await expect(refreshAccessToken()).rejects.toBeInstanceOf(ApiError)
  })
})

describe('error unwrapping', () => {
  it('turns the envelope into a typed ApiError', async () => {
    mock.onPost('/loans').reply(409, {
      error: {
        code: 'LOAN_LIMIT_REACHED',
        message: 'Member already has 5 active loans.',
        details: { limit: 5 },
      },
    })

    await expect(api.post('/loans', {})).rejects.toMatchObject({
      code: 'LOAN_LIMIT_REACHED',
      status: 409,
      message: 'Member already has 5 active loans.',
      details: { limit: 5 },
    })
  })

  it('exposes validation details as field errors', async () => {
    mock.onPost('/books').reply(400, {
      error: {
        code: 'VALIDATION_ERROR',
        message: 'The submitted data was invalid.',
        details: { isbn: ['Enter a valid ISBN-10 or ISBN-13.'] },
      },
    })

    try {
      await api.post('/books', {})
      expect.unreachable('the request should have failed')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).fieldErrors).toEqual({
        isbn: 'Enter a valid ISBN-10 or ISBN-13.',
      })
    }
  })

  it('describes an unreachable server in plain language', async () => {
    mock.onGet('/books').networkError()

    await expect(api.get('/books')).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
  })
})
