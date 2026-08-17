import { errorMessage } from '@/api/errors'
import { ReservationStatusBadge } from '@/components/Badge'
import { Button } from '@/components/Button'
import { useToast } from '@/components/toast-context'
import { EmptyState, ErrorState, PageHeading, RowsSkeleton } from '@/components/states'
import {
  useCancelReservation,
  useFulfilReservation,
  useReservations,
} from '@/features/circulation/hooks'
import { formatDate } from '@/lib/format'

export function HoldsPage() {
  const reservations = useReservations({ status: 'active' })
  const fulfil = useFulfilReservation()
  const cancel = useCancelReservation()
  const toast = useToast()

  const ready = reservations.data?.results.filter((item) => item.status === 'READY') ?? []
  const waiting = reservations.data?.results.filter((item) => item.status === 'PENDING') ?? []

  return (
    <>
      <PageHeading title="Holds" subtitle="The hold shelf, and who is waiting behind it." />

      {reservations.isPending && <RowsSkeleton rows={5} />}
      {reservations.isError && (
        <ErrorState error={reservations.error} onRetry={() => reservations.refetch()} />
      )}

      {reservations.data && (
        <>
          <section aria-labelledby="ready-heading">
            <h2 id="ready-heading" className="font-display text-xl font-semibold text-ink">
              On the hold shelf
            </h2>

            <div className="mt-4 space-y-3">
              {ready.length === 0 && (
                <EmptyState
                  title="Hold shelf is empty"
                  description="Copies land here when they come back for someone who is waiting."
                />
              )}

              {ready.map((reservation) => (
                <article
                  key={reservation.id}
                  className="flex flex-wrap items-center gap-4 rounded-sm border border-brass/50 bg-brass/5 p-4"
                >
                  <div className="min-w-[14rem] flex-1">
                    <p className="font-medium text-ink">{reservation.book.title}</p>
                    <p className="catalogue-data mt-0.5">
                      {reservation.held_copy?.call_number || '—'} ·{' '}
                      {reservation.held_copy?.barcode ?? 'no copy attached'}
                    </p>
                  </div>

                  <div className="text-sm">
                    <p className="text-ink">{reservation.member.full_name}</p>
                    <p className="catalogue-data">{reservation.member.membership_number}</p>
                  </div>

                  <p className="text-sm text-ink/60">
                    Held until {formatDate(reservation.expires_on)}
                  </p>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      loading={fulfil.isPending && fulfil.variables === reservation.id}
                      onClick={() =>
                        fulfil.mutate(reservation.id, {
                          onSuccess: (loan) =>
                            toast.success(
                              `Checked out to ${loan.member.full_name} — due ${formatDate(loan.due_on)}.`,
                            ),
                          onError: (error) => toast.error(errorMessage(error)),
                        })
                      }
                    >
                      Check out
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        cancel.mutate(reservation.id, {
                          onSuccess: () => toast.success('Hold cancelled.'),
                          onError: (error) => toast.error(errorMessage(error)),
                        })
                      }
                    >
                      Cancel
                    </Button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section aria-labelledby="waiting-heading" className="mt-12">
            <h2 id="waiting-heading" className="font-display text-xl font-semibold text-ink">
              Waiting
            </h2>

            <div className="mt-4 space-y-3">
              {waiting.length === 0 && (
                <EmptyState title="Nobody is queueing" description="Every reservation has a copy." />
              )}

              {waiting.map((reservation) => (
                <article
                  key={reservation.id}
                  className="flex flex-wrap items-center gap-4 rounded-sm border border-rule bg-white p-4"
                >
                  <span
                    aria-hidden="true"
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-rule font-mono text-sm text-ink/70"
                  >
                    {reservation.queue_position}
                  </span>
                  <div className="min-w-[14rem] flex-1">
                    <p className="font-medium text-ink">{reservation.book.title}</p>
                    <p className="mt-0.5 text-sm text-ink/55">
                      Reserved {formatDate(reservation.reserved_at)}
                    </p>
                  </div>
                  <div className="text-sm">
                    <p className="text-ink">{reservation.member.full_name}</p>
                    <p className="catalogue-data">{reservation.member.membership_number}</p>
                  </div>
                  <ReservationStatusBadge status={reservation.status} />
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </>
  )
}
