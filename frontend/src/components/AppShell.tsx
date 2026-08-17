import { NavLink, Outlet } from 'react-router-dom'

import { cn } from '@/lib/cn'
import { useAuthStore } from '@/features/auth/store'
import { useLogout } from '@/features/auth/hooks'
import { Button } from './Button'

const MEMBER_LINKS = [
  { to: '/catalogue', label: 'Catalogue' },
  { to: '/shelf', label: 'My shelf' },
]

const LIBRARIAN_LINKS = [
  { to: '/desk', label: 'Dashboard' },
  { to: '/desk/checkout', label: 'Check out' },
  { to: '/desk/checkin', label: 'Check in' },
  { to: '/desk/loans', label: 'Loans' },
  { to: '/desk/holds', label: 'Holds' },
  { to: '/desk/fines', label: 'Fines' },
  { to: '/desk/members', label: 'Members' },
  { to: '/catalogue', label: 'Catalogue' },
]

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === '/desk'}
      className={({ isActive }) =>
        cn(
          'rounded-sm px-3 py-1.5 text-sm transition-colors',
          isActive ? 'bg-ink/5 font-medium text-ink' : 'text-ink/60 hover:bg-ink/5 hover:text-ink',
        )
      }
    >
      {label}
    </NavLink>
  )
}

export function AppShell() {
  const user = useAuthStore((state) => state.user)
  const logout = useLogout()
  const links = user?.role === 'LIBRARIAN' ? LIBRARIAN_LINKS : MEMBER_LINKS

  return (
    <div className="min-h-screen bg-paper">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-sm focus:bg-ink focus:px-4 focus:py-2 focus:text-paper"
      >
        Skip to content
      </a>

      <header className="border-b border-rule bg-paper/95 backdrop-blur supports-[backdrop-filter]:bg-paper/80 sticky top-0 z-40">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
          <NavLink to="/" className="flex items-baseline gap-2">
            <span className="font-display text-xl font-semibold tracking-tight text-ink">
              The Library
            </span>
            <span className="hidden text-[0.625rem] uppercase tracking-[0.2em] text-ink/40 sm:inline">
              {user?.role === 'LIBRARIAN' ? 'Staff desk' : 'Members'}
            </span>
          </NavLink>

          <nav className="order-3 -mx-1 flex w-full flex-wrap items-center gap-1 sm:order-none sm:mx-0 sm:w-auto">
            {links.map((link) => (
              <NavItem key={link.to} {...link} />
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium leading-tight text-ink">{user?.full_name}</p>
              {user?.profile && (
                <p className="catalogue-data leading-tight">{user.profile.membership_number}</p>
              )}
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => logout.mutate()}
              loading={logout.isPending}
            >
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
        <Outlet />
      </main>

      <footer className="border-t border-rule py-6">
        <div className="mx-auto max-w-7xl px-4 text-xs text-ink/40 sm:px-6">
          Catalogued and circulating since 1897.
        </div>
      </footer>
    </div>
  )
}
