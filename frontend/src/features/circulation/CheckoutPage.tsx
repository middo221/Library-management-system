import { useEffect, useRef, useState } from 'react'

import { errorMessage } from '@/api/errors'
import type { MemberListItem } from '@/api/types'
import { Button } from '@/components/Button'
import { useToast } from '@/components/toast-context'
import { PageHeading } from '@/components/states'
import { useCheckout } from '@/features/circulation/hooks'
import { useMembers } from '@/features/members/hooks'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { cn } from '@/lib/cn'
import { formatDate, formatMoney } from '@/lib/format'

/**
 * The screen someone stands at all day, so it is built for a keyboard and a scanner:
 * scan a barcode → Enter → type a name or membership number → Enter picks the highlighted
 * member → Enter confirms. The mouse is optional throughout.
 */
export function CheckoutPage() {
  const [barcode, setBarcode] = useState('')
  const [memberQuery, setMemberQuery] = useState('')
  const [selected, setSelected] = useState<MemberListItem | null>(null)
  const [highlight, setHighlight] = useState(0)
  const [lastResult, setLastResult] = useState<string | null>(null)

  const barcodeRef = useRef<HTMLInputElement>(null)
  const memberRef = useRef<HTMLInputElement>(null)
  const confirmRef = useRef<HTMLButtonElement>(null)

  const toast = useToast()
  const checkout = useCheckout()
  const debouncedQuery = useDebouncedValue(memberQuery, 250)
  const members = useMembers({ search: debouncedQuery || undefined })
  const results = selected ? [] : (members.data?.results ?? [])

  useEffect(() => setHighlight(0), [debouncedQuery])

  const reset = () => {
    setBarcode('')
    setMemberQuery('')
    setSelected(null)
    barcodeRef.current?.focus()
  }

  const chooseMember = (member: MemberListItem) => {
    setSelected(member)
    setMemberQuery('')
    window.setTimeout(() => confirmRef.current?.focus(), 0)
  }

  const submit = () => {
    if (!barcode.trim() || !selected) return
    checkout.mutate(
      { barcode: barcode.trim(), member_id: selected.id },
      {
        onSuccess: (loan) => {
          setLastResult(
            `${loan.book.title} checked out to ${loan.member.full_name} — due ${formatDate(loan.due_on)}.`,
          )
          toast.success(`Checked out. Due ${formatDate(loan.due_on)}.`)
          reset()
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    )
  }

  return (
    <>
      <PageHeading
        title="Check out"
        subtitle="Scan the barcode, find the member, confirm. Enter moves you through."
      />

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-6">
          <section className="rounded-sm border border-rule bg-white p-5">
            <label htmlFor="barcode" className="field-label">
              1 · Barcode
            </label>
            <input
              id="barcode"
              ref={barcodeRef}
              autoFocus
              value={barcode}
              onChange={(event) => setBarcode(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  if (barcode.trim()) memberRef.current?.focus()
                }
              }}
              placeholder="Scan or type"
              className="field-input font-mono text-lg"
              autoComplete="off"
              spellCheck={false}
            />
          </section>

          <section className="rounded-sm border border-rule bg-white p-5">
            <label htmlFor="member" className="field-label">
              2 · Member
            </label>

            {selected ? (
              <div className="mt-2 flex flex-wrap items-center justify-between gap-3 rounded-sm border border-shelf/30 bg-shelf/5 px-4 py-3">
                <div>
                  <p className="font-medium text-ink">{selected.full_name}</p>
                  <p className="catalogue-data">{selected.membership_number}</p>
                </div>
                <div className="text-right text-sm text-ink/60">
                  <p>
                    {selected.active_loan_count} on loan
                    {selected.is_suspended && <span className="ml-2 text-stamp">Suspended</span>}
                  </p>
                  {Number.parseFloat(selected.unpaid_fine_total) > 0 && (
                    <p className="text-stamp">{formatMoney(selected.unpaid_fine_total)} owed</p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSelected(null)
                    window.setTimeout(() => memberRef.current?.focus(), 0)
                  }}
                >
                  Change
                </Button>
              </div>
            ) : (
              <>
                <input
                  id="member"
                  ref={memberRef}
                  value={memberQuery}
                  onChange={(event) => setMemberQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'ArrowDown') {
                      event.preventDefault()
                      setHighlight((index) => Math.min(index + 1, results.length - 1))
                    } else if (event.key === 'ArrowUp') {
                      event.preventDefault()
                      setHighlight((index) => Math.max(index - 1, 0))
                    } else if (event.key === 'Enter') {
                      event.preventDefault()
                      const member = results[highlight]
                      if (member) chooseMember(member)
                    }
                  }}
                  placeholder="Name, email or membership number"
                  className="field-input"
                  autoComplete="off"
                  role="combobox"
                  aria-expanded={results.length > 0}
                  aria-controls="member-results"
                />

                {results.length > 0 && (
                  <ul
                    id="member-results"
                    className="mt-3 max-h-72 overflow-y-auto rounded-sm border border-rule"
                    role="listbox"
                  >
                    {results.map((member, index) => (
                      <li key={member.id}>
                        <button
                          type="button"
                          role="option"
                          aria-selected={index === highlight}
                          onMouseEnter={() => setHighlight(index)}
                          onClick={() => chooseMember(member)}
                          className={cn(
                            'flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-sm',
                            index === highlight ? 'bg-ink/5' : 'bg-white hover:bg-ink/5',
                          )}
                        >
                          <span>
                            <span className="font-medium text-ink">{member.full_name}</span>
                            <span className="ml-2 text-ink/50">{member.email}</span>
                          </span>
                          <span className="catalogue-data">{member.membership_number}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                {debouncedQuery && !members.isPending && results.length === 0 && (
                  <p className="mt-3 text-sm text-ink/55">
                    No member matches that. Try the membership number.
                  </p>
                )}
              </>
            )}
          </section>

          <section className="rounded-sm border border-rule bg-white p-5">
            <p className="field-label">3 · Confirm</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Button
                ref={confirmRef}
                onClick={submit}
                loading={checkout.isPending}
                disabled={!barcode.trim() || !selected}
              >
                {checkout.isPending ? 'Checking out' : 'Check out'}
              </Button>
              <Button variant="ghost" onClick={reset} type="button">
                Clear
              </Button>
            </div>
          </section>
        </div>

        <aside className="space-y-4">
          <div className="rounded-sm border border-rule bg-white p-5" aria-live="polite">
            <p className="field-label">Last action</p>
            {lastResult ? (
              <p className="mt-3 text-sm text-ink/80">{lastResult}</p>
            ) : (
              <p className="mt-3 text-sm text-ink/50">Nothing checked out yet this session.</p>
            )}
          </div>

          <div className="rounded-sm border border-rule bg-white p-5">
            <p className="field-label">Keyboard</p>
            <dl className="mt-3 space-y-2 text-sm text-ink/65">
              <div className="flex justify-between gap-4">
                <dt>Barcode → member</dt>
                <dd className="catalogue-data">Enter</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt>Move through results</dt>
                <dd className="catalogue-data">↑ ↓</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt>Pick a member</dt>
                <dd className="catalogue-data">Enter</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt>Confirm</dt>
                <dd className="catalogue-data">Enter</dd>
              </div>
            </dl>
          </div>
        </aside>
      </div>
    </>
  )
}
