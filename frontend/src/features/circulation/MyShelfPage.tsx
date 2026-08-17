import { Link } from 'react-router-dom'

import { errorMessage } from '@/api/errors'
import type { Fine, Loan, Reservation } from '@/api/types'
import { Badge, FineStatusBadge, ReservationStatusBadge } from '@/components/Badge'
import { Button } from '@/components/Button'
import { DateStamp } from '@/components/DateStamp'
import { useToast } from '@/components/toast-context'
import { EmptyState, ErrorState, PageHeading, RowsSkeleton } from '@/components/states'
import {
  useCancelReservation,
  useMyFines,
  useMyLoans,
  useMyReservations,
  useRenew,
} from '@/features/circulation/hooks'
import { describeDueDate, formatDate, formatMoney } from '@/lib/format'

function LoanCard({ loan }: { loan: Loan }) {
  const renew = useRenew()
  const toast = useToast()

  const renewalsLeft = 2 - loan.renewal_count
  const blockedReason = loan.is_overdue
    ? 'Overdue loans are renewed at the desk.'
    : renewalsLeft <= 0
      ? 'This loan has been renewed the maximum number of times.'
      : null

  return (
    <article className="flex flex-wrap items-start gap-5 rounded-sm border border-rule bg-white p-5">
      <DateStamp date={loan.due_on} overdue={loan.is_overdue} />

      <div className="min-w-[12rem] flex-1">
        <Link
          to={`/catalogue/${loan.book.id}`}
          className="font-display text-lg font-semibold leading-snug text-ink hover:text-shelf"
        >
          {loan.book.title}
        </Link>
        <p className="mt-1 text-sm text-ink/60">{loan.book.authors.join(', ')}</p>

        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="catalogue-data">{loan.copy.call_number || loan.copy.barcode}</span>
          <span
            className={
              loan.is_overdue ? 'text-sm font-medium text-stamp' : 'text-sm text-ink/60'
            }
          >
            {describeDueDate(loan.due_on, loan.is_overdue, loan.days_overdue)}
          </span>
          {loan.renewal_count > 0 && (
            <Badge>
              Renewed {loan.renewal_count}×
            </Badge>
          )}
        </div>
      </div>

      <div className="flex flex-col items-end gap-1.5">
        <Button
          variant="secondary"
          size="sm"
          disabled={Boolean(blockedReason)}
          loading={renew.isPending}
          onClick={() =>
            renew.mutate(loan.id, {
              onSuccess: (updated) => toast.success(`Renewed — now due ${formatDate(updated.due_on)}.`),
              onError: (error) => toast.error(errorMessage(error)),
            })
          }
        >
          Renew
        </Button>
        {blockedReason && <p className="max-w-[14rem] text-right text-xs text-ink/50">{blockedReason}</p>}
      </div>
    </article>
  )
}

function ReservationRow({ reservation }: { reservation: Reservation }) {
  const cancel = useCancelReservation()
  const toast = useToast()

  return (
    <article className="flex flex-wrap items-center gap-4 rounded-sm border border-rule bg-white p-4">
      {reservation.status === 'PENDING' && (
        <span
          aria-hidden="true"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-rule font-mono text-sm text-ink/70"
        >
          {reservation.queue_position}
        </span>
      )}

      <div className="min-w-[12rem] flex-1">
        <Link
          to={`/catalogue/${reservation.book.id}`}
          className="font-medium text-ink hover:text-shelf"
        >
          {reservation.book.title}
        </Link>
        <p className="mt-0.5 text-sm text-ink/55">
          {reservation.status === 'PENDING' && (
            <>
              Number {reservation.queue_position} in the queue · reserved{' '}
              {formatDate(reservation.reserved_at)}
            </>
          )}
          {reservation.status === 'READY' && (
            <>Waiting at the desk until {formatDate(reservation.expires_on)}</>
          )}
          {!['PENDING', 'READY'].includes(reservation.status) && (
            <>Reserved {formatDate(reservation.reserved_at)}</>
          )}
        </p>
      </div>

      <ReservationStatusBadge status={reservation.status} />

      {['PENDING', 'READY'].includes(reservation.status) && (
        <Button
          variant="ghost"
          size="sm"
          loading={cancel.isPending}
          onClick={() =>
            cancel.mutate(reservation.id, {
              onSuccess: () => toast.success('Reservation cancelled.'),
              onError: (error) => toast.error(errorMessage(error)),
            })
          }
        >
          Cancel
        </Button>
      )}
    </article>
  )
}

function FineRow({ fine }: { fine: Fine }) {
  return (
    <article className="flex flex-wrap items-center justify-between gap-4 rounded-sm border border-rule bg-white p-4">
      <div>
        <p className="font-medium text-ink">{fine.book_title}</p>
        <p className="mt-0.5 text-sm text-ink/55">
          {fine.reason === 'OVERDUE' ? 'Overdue' : fine.reason === 'DAMAGE' ? 'Damage' : 'Lost'} ·
          assessed {formatDate(fine.assessed_on)}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <span
          className={
            fine.status === 'OUTSTANDING'
              ? 'font-mono text-lg text-stamp'
              : 'font-mono text-lg text-ink/50 line-through'
          }
        >
          {formatMoney(fine.amount)}
        </span>
        <FineStatusBadge status={fine.status} />
      </div>
    </article>
  )
}

export function MyShelfPage() {
  const loans = useMyLoans('active')
  const reservations = useMyReservations()
  const fines = useMyFines()

  const owed =
    fines.data?.results
      .filter((fine) => fine.status === 'OUTSTANDING')
      .reduce((total, fine) => total + Number.parseFloat(fine.amount), 0) ?? 0

  return (
    <>
      <PageHeading
        title="My shelf"
        subtitle="What you have out, what you are waiting for, and anything owed."
        actions={
          owed > 0 ? (
            <span className="rounded-sm border border-stamp/30 bg-stamp/10 px-3 py-1.5 text-sm font-medium text-stamp">
              {formatMoney(owed)} owed
            </span>
          ) : undefined
        }
      />

      <section aria-labelledby="loans-heading">
        <h2 id="loans-heading" className="font-display text-xl font-semibold text-ink">
          On loan
        </h2>

        <div className="mt-4 space-y-4">
          {loans.isPending && <RowsSkeleton rows={3} />}
          {loans.isError && <ErrorState error={loans.error} onRetry={() => loans.refetch()} />}
          {loans.data?.results.length === 0 && (
            <EmptyState
              title="No loans yet"
              description="Browse the catalogue to get started."
              action={
                <Link
                  to="/catalogue"
                  className="rounded-sm bg-shelf px-4 py-2.5 text-sm font-medium text-paper hover:bg-shelf/90"
                >
                  Browse the catalogue
                </Link>
              }
            />
          )}
          {loans.data?.results.map((loan) => <LoanCard key={loan.id} loan={loan} />)}
        </div>
      </section>

      <section aria-labelledby="holds-heading" className="mt-12">
        <h2 id="holds-heading" className="font-display text-xl font-semibold text-ink">
          Reservations
        </h2>

        <div className="mt-4 space-y-3">
          {reservations.isPending && <RowsSkeleton rows={2} />}
          {reservations.data?.results.length === 0 && (
            <EmptyState
              title="Nothing reserved"
              description="When a title is all out, reserve it and we'll hold the next copy back for you."
            />
          )}
          {reservations.data?.results.map((reservation) => (
            <ReservationRow key={reservation.id} reservation={reservation} />
          ))}
        </div>
      </section>

      <section aria-labelledby="fines-heading" className="mt-12">
        <h2 id="fines-heading" className="font-display text-xl font-semibold text-ink">
          Fines
        </h2>

        <div className="mt-4 space-y-3">
          {fines.isPending && <RowsSkeleton rows={1} />}
          {fines.data?.results.length === 0 && (
            <EmptyState title="Nothing owed" description="Everything has come back on time." />
          )}
          {fines.data?.results.map((fine) => <FineRow key={fine.id} fine={fine} />)}
        </div>
      </section>
    </>
  )
}
