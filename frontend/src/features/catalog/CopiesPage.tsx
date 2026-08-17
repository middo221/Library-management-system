import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { errorMessage } from '@/api/errors'
import { CopyStatusBadge } from '@/components/Badge'
import { Button } from '@/components/Button'
import { useToast } from '@/components/toast-context'
import { EmptyState, ErrorState, PageHeading, RowsSkeleton } from '@/components/states'
import { useAddCopy, useBook, useCopies, useDeleteCopy } from '@/features/catalog/hooks'
import { formatDate } from '@/lib/format'

export function CopiesPage() {
  const { bookId } = useParams()
  const id = Number(bookId)

  const book = useBook(id)
  const copies = useCopies(id)
  const addCopy = useAddCopy(id)
  const deleteCopy = useDeleteCopy()
  const toast = useToast()

  const [barcode, setBarcode] = useState('')
  const [callNumber, setCallNumber] = useState('')

  if (book.isPending) return <RowsSkeleton rows={3} />
  if (book.isError) return <ErrorState error={book.error} onRetry={() => book.refetch()} />

  const submit = () => {
    if (!barcode.trim()) return
    addCopy.mutate(
      { barcode: barcode.trim(), call_number: callNumber.trim() },
      {
        onSuccess: (copy) => {
          toast.success(`Copy ${copy.barcode} added.`)
          setBarcode('')
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    )
  }

  return (
    <>
      <Link
        to={`/catalogue/${id}`}
        className="text-sm text-ink/50 underline-offset-4 hover:text-ink hover:underline"
      >
        ← {book.data?.title}
      </Link>

      <PageHeading title="Copies" subtitle="The physical objects on the shelf, one row each." />

      <div className="max-w-3xl space-y-8">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            submit()
          }}
          className="rounded-sm border border-rule bg-white p-5"
        >
          <p className="field-label">Add a copy</p>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <div className="min-w-[12rem] flex-1">
              <label htmlFor="new-barcode" className="field-label">
                Barcode
              </label>
              <input
                id="new-barcode"
                value={barcode}
                onChange={(event) => setBarcode(event.target.value)}
                className="field-input font-mono"
                autoComplete="off"
              />
            </div>
            <div className="min-w-[12rem] flex-1">
              <label htmlFor="new-call-number" className="field-label">
                Call number
              </label>
              <input
                id="new-call-number"
                value={callNumber}
                onChange={(event) => setCallNumber(event.target.value)}
                placeholder="823.912 JOY"
                className="field-input font-mono"
                autoComplete="off"
              />
            </div>
            <Button type="submit" loading={addCopy.isPending} disabled={!barcode.trim()}>
              Add copy
            </Button>
          </div>
        </form>

        <div className="space-y-3">
          {copies.isPending && <RowsSkeleton rows={3} />}
          {copies.data?.length === 0 && (
            <EmptyState
              title="No copies yet"
              description="Add one above and this title starts circulating."
            />
          )}

          {copies.data?.map((copy) => (
            <div
              key={copy.id}
              className="flex flex-wrap items-center justify-between gap-4 rounded-sm border border-rule bg-white p-4"
            >
              <div>
                <p className="catalogue-data text-ink">{copy.call_number || '—'}</p>
                <p className="catalogue-data text-xs opacity-70">{copy.barcode}</p>
              </div>
              <p className="text-sm text-ink/55">Acquired {formatDate(copy.acquired_on)}</p>
              <CopyStatusBadge status={copy.status} />
              <Button
                variant="danger"
                size="sm"
                disabled={copy.status === 'ON_LOAN'}
                loading={deleteCopy.isPending && deleteCopy.variables === copy.id}
                onClick={() => {
                  if (!window.confirm(`Remove copy ${copy.barcode}?`)) return
                  deleteCopy.mutate(copy.id, {
                    onSuccess: () => toast.success('Copy removed.'),
                    onError: (error) => toast.error(errorMessage(error)),
                  })
                }}
              >
                Remove
              </Button>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
