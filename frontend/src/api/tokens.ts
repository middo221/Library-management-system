/**
 * Token storage.
 *
 * The access token lives in memory only — a page refresh loses it, and the app bootstraps a
 * new one from the refresh token on mount. The refresh token sits in localStorage, which is
 * the standard stateless-SPA tradeoff: it is reachable by XSS, and the fifteen-minute access
 * lifetime is what limits the blast radius. See docs/decisions.md; switching to an httpOnly
 * cookie is a backend change plus CSRF protection on /auth/refresh.
 */

const REFRESH_STORAGE_KEY = 'library.refresh_token'

let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getRefreshToken(): string | null {
  try {
    return window.localStorage.getItem(REFRESH_STORAGE_KEY)
  } catch {
    // Private browsing modes can throw on storage access; treat it as signed out.
    return null
  }
}

export function setRefreshToken(token: string | null): void {
  try {
    if (token === null) window.localStorage.removeItem(REFRESH_STORAGE_KEY)
    else window.localStorage.setItem(REFRESH_STORAGE_KEY, token)
  } catch {
    /* storage unavailable — the session simply will not survive a reload */
  }
}

export function clearTokens(): void {
  setAccessToken(null)
  setRefreshToken(null)
}
