import { useState } from 'react'

import { errorMessage } from '@/api/errors'
import { FineStatusBadge } from '@/components/Badge'
import { Button } from '@/components/Button'
import { useToast } from '@/components/toast-context'
import { EmptyState, ErrorState, PageHeading, RowsSkeleton } from '@/components/states'
import { useFines, usePayFine, useWaiveFine } from '@/features/circulation/hooks'
import { cn } from '@/lib/cn'
import { formatDate, formatMoney } from '@/lib/format'

const FILTERS = [
  { value: 'outstanding', label: 'Owed' },
  { value: 'paid', label: 'Paid' },
  { value: 'waived', label: 'Waived' },
  { value: '', label: 'Everything' },
] as const

export function FinesPage() {
  const [status, setStatus] = useState<string>('outstanding')
  const [waiving, setWaiving] = useState<number | null>(null)
  const [reason, setReason] = useState('')

  const fines = useFines({ status: status || undefined })
  const pay = usePayFine()
  const waive = useWaiveFine()
  const toast = useToast()

  const total =
    fines.data?.results
      .filter((fine) => fine.status === 'OUTSTANDING')
      .reduce((sum, fine) => sum + Number.parseFloat(fine.amount), 0) ?? 0

  const submitWaiver = (fineId: number) => {
    if (!reason.trim()) {
      toast.error('A reason is required to waive a fine.')
      return
    }
    waive.mutate(
      { id: fineId, reason: reason.trim() },
      {
        onSuccess: () => {
          toast.success('Fine waived.')
          setWaiving(null)
          setReason('')
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    )
  }

  return (
    <>
      <PageHeading
        title="Fines"
        subtitle="Assessed automatically on overdue returns; settled here by hand."
        actions={
          total > 0 ? (
            <span className="rounded-sm border border-stamp/30 bg-stamp/10 px-3 py-1.5 text-sm font-medium text-stamp">
              {formatMoney(total)} outstanding
            </span>
          ) : undefined
        }
      />

      <div role="tablist" aria-label="Fine status" className="mb-6 flex flex-wrap gap-1">
        {FILTERS.map((filter) => (
          <button
            key={filter.value || 'all'}
            role="tab"
            aria-selected={status === filter.value}
            onClick={() => setStatus(filter.value)}
            className={cn(
              'rounded-sm px-3 py-1.5 text-sm transition-colors',
              status === filter.value
                ? 'bg-ink text-paper'
                : 'border border-rule bg-white text-ink/70 hover:text-ink',
            )}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {fines.isPending && <RowsSkeleton rows={5} />}
      {fines.isError && <ErrorState error={fines.error} onRetry={() => fines.refetch()} />}

      {fines.data?.results.length === 0 && (
        <EmptyState
          title="Nothing here"
          description={status === 'outstanding' ? 'No fines are owed.' : 'No fines match that filter.'}
        />
      )}

      <div className="space-y-3">
        {fines.data?.results.map((fine) => (
          <article key={fine.id} className="rounded-sm border border-rule bg-white p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="min-w-[14rem] flex-1">
                <p className="font-medium text-ink">{fine.book_title}</p>
                <p className="mt-0.5 text-sm text-ink/55">
                  {fine.member.full_name} ·{' '}
                  <span className="catalogue-data">{fine.member.membership_number}</span> ·{' '}
                  {fine.reason.toLowerCase()} · {formatDate(fine.assessed_on)}
                </p>
              </div>

              <span
                className={cn(
                  'font-mono text-lg',
                  fine.status === 'OUTSTANDING' ? 'text-stamp' : 'text-ink/50 line-through',
                )}
              >
                {formatMoney(fine.amount)}
              </span>

              <FineStatusBadge status={fine.status} />

              {fine.status === 'OUTSTANDING' && (
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    loading={pay.isPending && pay.variables === fine.id}
                    onClick={() =>
                      pay.mutate(fine.id, {
                        onSuccess: () => toast.success('Marked paid.'),
                        onError: (error) => toast.error(errorMessage(error)),
                      })
                    }
                  >
                    Mark paid
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setWaiving(waiving === fine.id ? null : fine.id)
                      setReason('')
                    }}
                  >
                    Waive
                  </Button>
                </div>
              )}
            </div>

            {fine.waiver_reason && (
              <p className="mt-3 border-t border-rule pt-3 text-sm text-ink/55">
                Waived: {fine.waiver_reason}
              </p>
            )}

            {waiving === fine.id && (
              <div className="mt-4 border-t border-rule pt-4">
                <label htmlFor={`waive-${fine.id}`} className="field-label">
                  Reason for waiving
                </label>
                <div className="mt-1.5 flex flex-wrap gap-2">
                  <input
                    id={`waive-${fine.id}`}
                    autoFocus
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault()
                        submitWaiver(fine.id)
                      }
                    }}
                    placeholder="Why is this being written off?"
                    className="field-input mt-0 flex-1"
                  />
                  <Button size="md" loading={waive.isPending} onClick={() => submitWaiver(fine.id)}>
                    Waive
                  </Button>
                  <Button variant="ghost" onClick={() => setWaiving(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </article>
        ))}
      </div>
    </>
  )
}
