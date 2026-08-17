import type { ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuthStore } from './store'

function Booting() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper">
      <div className="flex items-center gap-3 text-sm text-ink/50">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-shelf border-t-transparent" />
        Opening the library…
      </div>
    </div>
  )
}

/** Requires a session. Remembers where you were headed so login can return you there. */
export function ProtectedRoute() {
  const user = useAuthStore((state) => state.user)
  const initialising = useAuthStore((state) => state.initialising)
  const location = useLocation()

  if (initialising) return <Booting />
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

/** Already signed in? The login and register pages have nothing to offer you. */
export function GuestOnlyRoute() {
  const user = useAuthStore((state) => state.user)
  const initialising = useAuthStore((state) => state.initialising)

  if (initialising) return <Booting />
  if (user) return <Navigate to={user.role === 'LIBRARIAN' ? '/desk' : '/shelf'} replace />
  return <Outlet />
}

/** Role gate for whole routes. Shows the 403 page, never a blank screen. */
export function RoleRoute({ role }: { role: 'LIBRARIAN' | 'MEMBER' }) {
  const user = useAuthStore((state) => state.user)
  const initialising = useAuthStore((state) => state.initialising)

  if (initialising) return <Booting />
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== role) return <Navigate to="/no-access" replace />
  return <Outlet />
}

/** Role gate for a fragment of a page — hides an action the server would refuse anyway. */
export function RoleGate({
  role,
  children,
  fallback = null,
}: {
  role: 'LIBRARIAN' | 'MEMBER'
  children: ReactNode
  fallback?: ReactNode
}) {
  const user = useAuthStore((state) => state.user)
  return user?.role === role ? <>{children}</> : <>{fallback}</>
}
