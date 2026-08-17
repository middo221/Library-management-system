import { Link, useNavigate, useParams } from 'react-router-dom'

import { errorMessage } from '@/api/errors'
import { AvailabilityBadge, CopyStatusBadge } from '@/components/Badge'
import { Button } from '@/components/Button'
import { useToast } from '@/components/toast-context'
import { ErrorState, RowsSkeleton } from '@/components/states'
import { RoleGate } from '@/features/auth/guards'
import { useAuthStore } from '@/features/auth/store'
import { useBook, useCopies, useDeleteBook } from '@/features/catalog/hooks'
import { useMyReservations, useReserve } from '@/features/circulation/hooks'
import { formatDate } from '@/lib/format'

export function BookDetailPage() {
  const { bookId } = useParams()
  const id = Number(bookId)
  const navigate = useNavigate()
  const toast = useToast()
  const user = useAuthStore((state) => state.user)

  const book = useBook(id)
  const copies = useCopies(id)
  const reserve = useReserve()
  const deleteBook = useDeleteBook()
  const myReservations = useMyReservations()

  if (book.isPending) return <RowsSkeleton rows={4} />
  if (book.isError) return <ErrorState error={book.error} onRetry={() => book.refetch()} />
  if (!book.data) return null

  const record = book.data
  const existingHold = myReservations.data?.results.find(
    (reservation) => reservation.book.id === id && ['PENDING', 'READY'].includes(reservation.status),
  )
  const canReserve = user?.role === 'MEMBER' && !existingHold

  const handleReserve = () => {
    reserve.mutate(
      { book_id: id },
      {
        onSuccess: (reservation) => {
          toast.success(
            reservation.status === 'READY'
              ? 'Reserved — a copy is being held for you at the desk.'
              : `Reserved. You are number ${reservation.queue_position} in the queue.`,
          )
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    )
  }

  const handleDelete = () => {
    if (!window.confirm(`Remove "${record.title}" from the catalogue?`)) return
    deleteBook.mutate(id, {
      onSuccess: () => {
        toast.success('Removed from the catalogue.')
        navigate('/catalogue')
      },
      onError: (error) => toast.error(errorMessage(error)),
    })
  }

  return (
    <>
      <Link
        to="/catalogue"
        className="text-sm text-ink/50 underline-offset-4 hover:text-ink hover:underline"
      >
        ← Catalogue
      </Link>

      <div className="mt-5 grid gap-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="catalogue-data">{record.isbn}</span>
            <AvailabilityBadge available={record.available_copies} total={record.total_copies} />
          </div>

          <h1 className="mt-4 font-display text-4xl font-semibold leading-tight tracking-tight text-ink">
            {record.title}
          </h1>
          {record.subtitle && <p className="mt-2 text-lg text-ink/60">{record.subtitle}</p>}

          <p className="mt-4 text-base text-ink/80">
            {record.authors.length
              ? record.authors.map((author) => author.name).join(', ')
              : 'Unattributed'}
          </p>

          {record.description && (
            <p className="mt-7 max-w-prose leading-relaxed text-ink/75">{record.description}</p>
          )}

          <dl className="mt-9 grid grid-cols-2 gap-x-8 gap-y-4 border-t border-rule pt-6 text-sm sm:grid-cols-3">
            <Detail label="Publisher" value={record.publisher || '—'} />
            <Detail label="Published" value={record.published_year?.toString() ?? '—'} />
            <Detail label="Language" value={record.language} />
            <Detail label="Pages" value={record.page_count?.toString() ?? '—'} />
            <Detail label="Category" value={record.category?.name ?? 'Uncategorised'} />
            <Detail label="Catalogued" value={formatDate(record.created_at)} />
          </dl>
        </div>

        <aside className="space-y-6">
          <div className="rounded-sm border border-rule bg-white p-5">
            <h2 className="font-display text-lg font-semibold text-ink">Copies</h2>

            {copies.isPending && <RowsSkeleton rows={2} />}
            {copies.data?.length === 0 && (
              <p className="mt-3 text-sm text-ink/55">
                No copies yet. A librarian needs to add one before this title can circulate.
              </p>
            )}

            <ul className="mt-4 space-y-3 rule-divide">
              {copies.data?.map((copy) => (
                <li key={copy.id} className="flex items-center justify-between gap-3 pt-3 first:pt-0">
                  <div>
                    <p className="catalogue-data text-ink">{copy.call_number || '—'}</p>
                    <p className="catalogue-data text-xs opacity-70">{copy.barcode}</p>
                  </div>
                  <CopyStatusBadge status={copy.status} />
                </li>
              ))}
            </ul>

            {canReserve && (
              <div className="mt-6 border-t border-rule pt-5">
                <Button
                  onClick={handleReserve}
                  loading={reserve.isPending}
                  className="w-full"
                >
                  {reserve.isPending ? 'Reserving' : 'Reserve'}
                </Button>
                <p className="mt-2 text-xs text-ink/50">
                  {record.available_copies > 0
                    ? 'A copy will be held at the desk for three days.'
                    : 'You will join the queue and be told when a copy comes back.'}
                </p>
              </div>
            )}

            {existingHold && (
              <p className="mt-6 border-t border-rule pt-5 text-sm text-shelf">
                {existingHold.status === 'READY'
                  ? 'A copy is waiting for you at the desk.'
                  : `You are number ${existingHold.queue_position} in the queue for this title.`}
              </p>
            )}
          </div>

          <RoleGate role="LIBRARIAN">
            <div className="rounded-sm border border-rule bg-white p-5">
              <h2 className="font-display text-lg font-semibold text-ink">Manage</h2>
              <div className="mt-4 flex flex-col gap-2">
                <Button variant="secondary" onClick={() => navigate(`/desk/catalogue/${id}/edit`)}>
                  Edit this record
                </Button>
                <Button
                  variant="danger"
                  onClick={handleDelete}
                  loading={deleteBook.isPending}
                >
                  Remove from catalogue
                </Button>
              </div>
              <p className="mt-3 text-xs text-ink/50">
                A title with copies cannot be removed. Withdraw the copies first.
              </p>
            </div>
          </RoleGate>
        </aside>
      </div>
    </>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="field-label">{label}</dt>
      <dd className="mt-1 text-ink/80">{value}</dd>
    </div>
  )
}
