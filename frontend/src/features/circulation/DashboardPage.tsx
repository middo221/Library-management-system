import { Link } from 'react-router-dom'

import { Badge } from '@/components/Badge'
import { EmptyState, ErrorState, PageHeading, RowsSkeleton, Skeleton } from '@/components/states'
import { useDashboardStats, useLoans } from '@/features/circulation/hooks'
import { formatMoney, pluralise } from '@/lib/format'

function Stat({
  label,
  value,
  tone = 'neutral',
  hint,
}: {
  label: string
  value: string | number
  tone?: 'neutral' | 'alert'
  hint?: string
}) {
  return (
    <div className="rounded-sm border border-rule bg-white p-5">
      <p className="field-label">{label}</p>
      <p
        className={
          tone === 'alert'
            ? 'mt-2 font-display text-3xl font-semibold text-stamp'
            : 'mt-2 font-display text-3xl font-semibold text-ink'
        }
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-ink/50">{hint}</p>}
    </div>
  )
}

export function DashboardPage() {
  const stats = useDashboardStats()
  const overdue = useLoans({ status: 'overdue', page_size: 8 })

  return (
    <>
      <PageHeading title="The desk" subtitle="Where the collection stands this morning." />

      {stats.isPending && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
      )}

      {stats.isError && <ErrorState error={stats.error} onRetry={() => stats.refetch()} />}

      {stats.data && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Stat label="Titles" value={stats.data.total_titles} hint={`${stats.data.total_copies} copies`} />
          <Stat
            label="On loan"
            value={stats.data.copies_on_loan}
            hint={`${stats.data.copies_available} on the shelf`}
          />
          <Stat
            label="Overdue"
            value={stats.data.loans_overdue}
            tone={stats.data.loans_overdue > 0 ? 'alert' : 'neutral'}
            hint={`${stats.data.loans_due_today} due today`}
          />
          <Stat
            label="Unpaid fines"
            value={formatMoney(stats.data.unpaid_fines_total)}
            tone={stats.data.unpaid_fines_count > 0 ? 'alert' : 'neutral'}
            hint={`${stats.data.unpaid_fines_count} outstanding`}
          />
          <Stat label="Active members" value={stats.data.active_members} hint={`${stats.data.suspended_members} suspended`} />
          <Stat label="Waiting" value={stats.data.reservations_waiting} hint="in reservation queues" />
          <Stat label="On the hold shelf" value={stats.data.reservations_ready} hint="ready to collect" />
          <Stat label="Live loans" value={stats.data.loans_active} />
        </div>
      )}

      <section className="mt-12" aria-labelledby="overdue-heading">
        <div className="flex items-end justify-between border-b border-rule pb-3">
          <h2 id="overdue-heading" className="font-display text-xl font-semibold text-ink">
            Overdue
          </h2>
          <Link
            to="/desk/loans?status=overdue"
            className="text-sm text-shelf underline underline-offset-4 hover:text-ink"
          >
            All loans
          </Link>
        </div>

        <div className="mt-5 space-y-3">
          {overdue.isPending && <RowsSkeleton rows={4} />}
          {overdue.data?.results.length === 0 && (
            <EmptyState title="Nothing overdue" description="Every loan is within its date." />
          )}
          {overdue.data?.results.map((loan) => (
            <div
              key={loan.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-sm border border-rule bg-white p-4"
            >
              <div className="min-w-[14rem] flex-1">
                <p className="font-medium text-ink">{loan.book.title}</p>
                <p className="catalogue-data mt-0.5">
                  {loan.copy.call_number || '—'} · {loan.copy.barcode}
                </p>
              </div>
              <div className="text-sm text-ink/60">
                {loan.member.full_name}{' '}
                <span className="catalogue-data">{loan.member.membership_number}</span>
              </div>
              <Badge tone="bad">
                {loan.days_overdue} {pluralise(loan.days_overdue, 'day')} overdue
              </Badge>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
