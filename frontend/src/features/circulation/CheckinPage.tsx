import { useRef, useState } from 'react'

import { errorMessage } from '@/api/errors'
import type { CheckinResult } from '@/api/types'
import { Button } from '@/components/Button'
import { useToast } from '@/components/toast-context'
import { PageHeading } from '@/components/states'
import { circulationApi } from '@/api/endpoints'
import { useCheckin } from '@/features/circulation/hooks'
import { cn } from '@/lib/cn'
import { formatMoney } from '@/lib/format'

type Outcome =
  | { kind: 'shelve'; result: CheckinResult }
  | { kind: 'hold'; result: CheckinResult }
  | { kind: 'fine'; result: CheckinResult }

function classify(result: CheckinResult): Outcome {
  if (result.hold) return { kind: 'hold', result }
  if (result.fine) return { kind: 'fine', result }
  return { kind: 'shelve', result }
}

const BANNER: Record<Outcome['kind'], { className: string; heading: string }> = {
  shelve: { className: 'border-shelf/40 bg-shelf/10 text-shelf', heading: 'Shelve it' },
  hold: { className: 'border-brass bg-brass/15 text-[#6E5527]', heading: 'Hold for a member' },
  fine: { className: 'border-stamp/40 bg-stamp/10 text-stamp', heading: 'Fine assessed' },
}

/**
 * One field, one prominent answer. The person doing this is holding a book and needs to know
 * in a glance whether it goes on the shelf, on the hold shelf, or to a conversation about a
 * fine.
 */
export function CheckinPage() {
  const [barcode, setBarcode] = useState('')
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [looking, setLooking] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const toast = useToast()
  const checkin = useCheckin()

  const submit = async () => {
    const value = barcode.trim()
    if (!value) return

    setLooking(true)
    try {
      // The API checks in by loan, so find the copy's live loan first.
      const loans = await circulationApi.listLoans({ status: 'active', search: value })
      const loan = loans.results.find((candidate) => candidate.copy.barcode === value)

      if (!loan) {
        toast.error(`No live loan for barcode ${value}. It may already be back on the shelf.`)
        return
      }

      checkin.mutate(loan.id, {
        onSuccess: (result) => {
          setOutcome(classify(result))
          setBarcode('')
          inputRef.current?.focus()
        },
        onError: (error) => toast.error(errorMessage(error)),
      })
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setLooking(false)
    }
  }

  const busy = looking || checkin.isPending

  return (
    <>
      <PageHeading title="Check in" subtitle="One barcode at a time. The banner tells you where it goes." />

      <div className="max-w-2xl">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void submit()
          }}
          className="rounded-sm border border-rule bg-white p-5"
        >
          <label htmlFor="checkin-barcode" className="field-label">
            Barcode
          </label>
          <div className="mt-1.5 flex gap-3">
            <input
              id="checkin-barcode"
              ref={inputRef}
              autoFocus
              value={barcode}
              onChange={(event) => setBarcode(event.target.value)}
              placeholder="Scan or type"
              className="field-input mt-0 font-mono text-lg"
              autoComplete="off"
              spellCheck={false}
            />
            <Button type="submit" loading={busy} disabled={!barcode.trim()}>
              {busy ? 'Checking in' : 'Check in'}
            </Button>
          </div>
        </form>

        <div className="mt-6" aria-live="polite">
          {outcome && (
            <div className={cn('rounded-sm border-2 p-6', BANNER[outcome.kind].className)}>
              <p className="font-display text-2xl font-semibold">{BANNER[outcome.kind].heading}</p>
              <p className="mt-2 text-base text-ink/80">{outcome.result.message}</p>

              <dl className="mt-5 grid gap-x-8 gap-y-3 border-t border-current/20 pt-4 text-sm text-ink/75 sm:grid-cols-2">
                <div>
                  <dt className="field-label">Title</dt>
                  <dd className="mt-1">{outcome.result.loan.book.title}</dd>
                </div>
                <div>
                  <dt className="field-label">Call number</dt>
                  <dd className="catalogue-data mt-1">
                    {outcome.result.loan.copy.call_number || '—'}
                  </dd>
                </div>
                <div>
                  <dt className="field-label">Returned by</dt>
                  <dd className="mt-1">
                    {outcome.result.loan.member.full_name}{' '}
                    <span className="catalogue-data">
                      {outcome.result.loan.member.membership_number}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="field-label">Copy is now</dt>
                  <dd className="mt-1">{outcome.result.copy_status.replace('_', ' ').toLowerCase()}</dd>
                </div>
                {outcome.result.fine && (
                  <div>
                    <dt className="field-label">Fine</dt>
                    <dd className="mt-1 font-mono">{formatMoney(outcome.result.fine.amount)}</dd>
                  </div>
                )}
                {outcome.result.hold && (
                  <div>
                    <dt className="field-label">Hold for</dt>
                    <dd className="mt-1">
                      {outcome.result.hold.member.full_name}{' '}
                      <span className="catalogue-data">
                        {outcome.result.hold.member.membership_number}
                      </span>
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          {!outcome && (
            <p className="rounded-sm border border-dashed border-rule px-6 py-10 text-center text-sm text-ink/50">
              Scan a barcode to check a copy back in.
            </p>
          )}
        </div>
      </div>
    </>
  )
}
