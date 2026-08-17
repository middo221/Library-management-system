import type { ReactNode } from 'react'

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col justify-center bg-paper px-4 py-12">
      <div className="mx-auto w-full max-w-md">
        <div className="mb-8 text-center">
          <p className="font-display text-3xl font-semibold tracking-tight text-ink">The Library</p>
          <p className="mt-1 text-[0.625rem] uppercase tracking-[0.25em] text-ink/40">
            Catalogue · Circulation · Membership
          </p>
        </div>

        <div className="rounded-sm border border-rule bg-white p-7 shadow-sm">
          <h1 className="font-display text-xl font-semibold text-ink">{title}</h1>
          <p className="mt-1 text-sm text-ink/60">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </div>

        {footer && <div className="mt-6 text-center">{footer}</div>}
      </div>
    </div>
  )
}
