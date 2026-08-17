import { create } from 'zustand'

import { clearTokens, setAccessToken, setRefreshToken } from '@/api/tokens'
import type { AuthResponse, User } from '@/api/types'

interface AuthState {
  user: User | null
  /** `true` until the bootstrap attempt finishes, so routes don't flash the login page. */
  initialising: boolean
  signIn: (payload: AuthResponse) => void
  setUser: (user: User | null) => void
  signOut: () => void
  finishInitialising: () => void
}

/**
 * Auth is the only client state that isn't server state, which is why it is the only thing
 * in Zustand. Everything else lives in TanStack Query.
 */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  initialising: true,

  signIn: ({ access, refresh, user }) => {
    setAccessToken(access)
    setRefreshToken(refresh)
    set({ user, initialising: false })
  },

  setUser: (user) => set({ user }),

  signOut: () => {
    clearTokens()
    set({ user: null, initialising: false })
  },

  finishInitialising: () => set({ initialising: false }),
}))

export const selectIsLibrarian = (state: AuthState) => state.user?.role === 'LIBRARIAN'
export const selectIsAuthenticated = (state: AuthState) => state.user !== null
