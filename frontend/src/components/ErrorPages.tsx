import { Link } from 'react-router-dom'

import { useAuthStore } from '@/features/auth/store'

function Notice({
  code,
  title,
  description,
  action,
}: {
  code: string
  title: string
  description: string
  action: { to: string; label: string }
}) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <p className="catalogue-data text-xs uppercase tracking-[0.3em]">{code}</p>
      <h1 className="mt-4 font-display text-3xl font-semibold text-ink">{title}</h1>
      <p className="mt-3 max-w-md text-sm text-ink/60">{description}</p>
      <Link
        to={action.to}
        className="mt-7 rounded-sm bg-shelf px-4 py-2.5 text-sm font-medium text-paper hover:bg-shelf/90"
      >
        {action.label}
      </Link>
    </div>
  )
}

export function NotFoundPage() {
  const user = useAuthStore((state) => state.user)
  return (
    <Notice
      code="404"
      title="Not on any shelf"
      description="That page isn't in the catalogue. It may have been moved, or the link may have a typo in it."
      action={
        user
          ? { to: '/catalogue', label: 'Browse the catalogue' }
          : { to: '/login', label: 'Sign in' }
      }
    />
  )
}

export function ForbiddenPage() {
  const user = useAuthStore((state) => state.user)
  return (
    <Notice
      code="403"
      title="Staff only"
      description="This part of the system is for librarians. Your membership gives you the catalogue, your shelf, and your reservations."
      action={
        user?.role === 'LIBRARIAN'
          ? { to: '/desk', label: 'Back to the desk' }
          : { to: '/shelf', label: 'Back to my shelf' }
      }
    />
  )
}
