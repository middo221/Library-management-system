import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { refreshAccessToken, SESSION_EXPIRED_EVENT } from '@/api/client'
import { authApi, type LoginPayload, type RegisterPayload } from '@/api/endpoints'
import { getRefreshToken } from '@/api/tokens'
import { useAuthStore } from './store'

/**
 * Restore the session on mount.
 *
 * A page refresh loses the in-memory access token, so we spend the refresh token to get a
 * new one before rendering any route. That is what makes a hard refresh on a deep link land
 * on that page instead of the login screen.
 */
export function useSessionBootstrap(): void {
  const setUser = useAuthStore((state) => state.setUser)
  const signOut = useAuthStore((state) => state.signOut)
  const finishInitialising = useAuthStore((state) => state.finishInitialising)
  const [started, setStarted] = useState(false)

  useEffect(() => {
    if (started) return
    setStarted(true)

    if (!getRefreshToken()) {
      finishInitialising()
      return
    }

    let cancelled = false
    refreshAccessToken()
      .then(() => authApi.me())
      .then((user) => {
        if (!cancelled) setUser(user)
      })
      .catch(() => {
        if (!cancelled) signOut()
      })
      .finally(() => {
        if (!cancelled) finishInitialising()
      })

    return () => {
      cancelled = true
    }
  }, [started, setUser, signOut, finishInitialising])
}

/** A failed refresh anywhere in the app ends the session everywhere. */
export function useSessionExpiryListener(): void {
  const signOut = useAuthStore((state) => state.signOut)
  const queryClient = useQueryClient()

  useEffect(() => {
    const handle = () => {
      signOut()
      queryClient.clear()
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, handle)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handle)
  }, [signOut, queryClient])
}

export function useLogin() {
  const signIn = useAuthStore((state) => state.signIn)
  return useMutation({
    mutationFn: (payload: LoginPayload) => authApi.login(payload),
    onSuccess: signIn,
  })
}

export function useRegister() {
  const signIn = useAuthStore((state) => state.signIn)
  return useMutation({
    mutationFn: (payload: RegisterPayload) => authApi.register(payload),
    onSuccess: signIn,
  })
}

export function useLogout() {
  const signOut = useAuthStore((state) => state.signOut)
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const refresh = getRefreshToken()
      // Best effort: an unreachable server must not trap someone in a signed-in shell.
      if (refresh) await authApi.logout(refresh).catch(() => undefined)
    },
    onSettled: () => {
      signOut()
      queryClient.clear()
    },
  })
}

export function useUpdateProfile() {
  const setUser = useAuthStore((state) => state.setUser)
  return useMutation({
    mutationFn: authApi.updateMe,
    onSuccess: setUser,
  })
}

export function useChangePassword() {
  return useMutation({ mutationFn: authApi.changePassword })
}
