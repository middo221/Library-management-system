import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'
import { errorMessage } from '@/api/errors'

/** Loading skeletons. Every list has one — a blank screen is never an acceptable state. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-sm bg-rule/50', className)} aria-hidden="true" />
}

export function RowsSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3" role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-16 w-full" />
      ))}
    </div>
  )
}

export function CardsSkeleton({ cards = 8 }: { cards?: number }) {
  return (
    <div
      className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      role="status"
      aria-label="Loading"
    >
      {Array.from({ length: cards }).map((_, index) => (
        <Skeleton key={index} className="h-52 w-full" />
      ))}
    </div>
  )
}

/** Empty states are invitations, not apologies. */
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="rounded-sm border border-dashed border-rule bg-white/60 px-6 py-14 text-center">
      <p className="font-display text-lg text-ink">{title}</p>
      {description && <p className="mx-auto mt-2 max-w-md text-sm text-ink/60">{description}</p>}
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  )
}

/** Errors state what happened and what to do about it. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="rounded-sm border border-stamp/30 bg-stamp/5 px-6 py-8 text-center"
    >
      <p className="font-display text-lg text-stamp">That didn't work</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-ink/70">{errorMessage(error)}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 text-sm font-medium text-shelf underline underline-offset-4 hover:text-ink"
        >
          Try again
        </button>
      )}
    </div>
  )
}

export function PageHeading({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1.5 text-sm text-ink/60">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
