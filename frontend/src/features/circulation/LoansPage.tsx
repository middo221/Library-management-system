import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { errorMessage } from '@/api/errors'
import { Badge } from '@/components/Badge'
import { Button } from '@/components/Button'
import { Pagination } from '@/components/Pagination'
import { useToast } from '@/components/toast-context'
import { EmptyState, ErrorState, PageHeading, RowsSkeleton } from '@/components/states'
import { useCheckin, useLoans } from '@/features/circulation/hooks'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { cn } from '@/lib/cn'
import { formatDate, pluralise } from '@/lib/format'

const FILTERS = [
  { value: 'active', label: 'Out now' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'returned', label: 'Returned' },
  { value: '', label: 'Everything' },
] as const

export function LoansPage() {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const status = (params.get('status') ?? 'active') as (typeof FILTERS)[number]['value']
  const debouncedSearch = useDebouncedValue(search)
  const loans = useLoans({ status, search: debouncedSearch || undefined, page, page_size: 20 })

  const checkin = useCheckin()
  const toast = useToast()

  return (
    <>
      <PageHeading title="Loans" subtitle="Everything that has left the building, and when it is back." />

      <div className="mb-6 flex flex-wrap items-end gap-4">
        <div role="tablist" aria-label="Loan status" className="flex flex-wrap gap-1">
          {FILTERS.map((filter) => (
            <button
              key={filter.value || 'all'}
              role="tab"
              aria-selected={status === filter.value}
              onClick={() => {
                setPage(1)
                setParams(filter.value ? { status: filter.value } : {})
              }}
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

        <div className="ml-auto min-w-[16rem]">
          <label htmlFor="loan-search" className="sr-only">
            Search loans
          </label>
          <input
            id="loan-search"
            type="search"
            value={search}
            onChange={(event) => {
              setPage(1)
              setSearch(event.target.value)
            }}
            placeholder="Barcode, title, email or membership number"
            className="field-input mt-0"
          />
        </div>
      </div>

      {loans.isPending && <RowsSkeleton rows={6} />}
      {loans.isError && <ErrorState error={loans.error} onRetry={() => loans.refetch()} />}

      {loans.data?.results.length === 0 && (
        <EmptyState
          title="No loans here"
          description={
            status === 'overdue'
              ? 'Everything is within its date.'
              : 'Nothing matches that filter yet.'
          }
        />
      )}

      {loans.data && loans.data.results.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-sm border border-rule bg-white">
            <table className="w-full min-w-[52rem] text-left text-sm">
              <thead className="border-b border-rule text-xs uppercase tracking-[0.1em] text-ink/50">
                <tr>
                  <th className="px-4 py-3 font-semibold">Call number</th>
                  <th className="px-4 py-3 font-semibold">Title</th>
                  <th className="px-4 py-3 font-semibold">Member</th>
                  <th className="px-4 py-3 font-semibold">Due</th>
                  <th className="px-4 py-3 font-semibold">State</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="rule-divide">
                {loans.data.results.map((loan) => (
                  <tr key={loan.id} className="transition-colors hover:bg-ink/[0.02]">
                    <td className="px-4 py-3">
                      <p className="catalogue-data text-ink">{loan.copy.call_number || '—'}</p>
                      <p className="catalogue-data text-xs opacity-70">{loan.copy.barcode}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-ink">{loan.book.title}</p>
                      <p className="text-xs text-ink/50">{loan.book.authors.join(', ')}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-ink">{loan.member.full_name}</p>
                      <p className="catalogue-data text-xs">{loan.member.membership_number}</p>
                    </td>
                    <td className="px-4 py-3 text-ink/70">{formatDate(loan.due_on)}</td>
                    <td className="px-4 py-3">
                      {loan.returned_at ? (
                        <Badge>Returned {formatDate(loan.returned_at)}</Badge>
                      ) : loan.is_overdue ? (
                        <Badge tone="bad">
                          {loan.days_overdue} {pluralise(loan.days_overdue, 'day')} overdue
                        </Badge>
                      ) : (
                        <Badge tone="good">Out</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {loan.is_active && (
                        <Button
                          variant="secondary"
                          size="sm"
                          loading={checkin.isPending && checkin.variables === loan.id}
                          onClick={() =>
                            checkin.mutate(loan.id, {
                              onSuccess: (result) => toast.success(result.message),
                              onError: (error) => toast.error(errorMessage(error)),
                            })
                          }
                        >
                          Check in
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination
            page={loans.data.page}
            totalPages={loans.data.total_pages}
            count={loans.data.count}
            onChange={setPage}
            noun="loan"
          />
        </>
      )}
    </>
  )
}
