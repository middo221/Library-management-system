import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { errorMessage } from '@/api/errors'
import { Badge } from '@/components/Badge'
import { Button } from '@/components/Button'
import { useToast } from '@/components/toast-context'
import { EmptyState, ErrorState, PageHeading, RowsSkeleton } from '@/components/states'
import { useLoans } from '@/features/circulation/hooks'
import { useMember, useUpdateMember } from '@/features/members/hooks'
import { formatDate, pluralise } from '@/lib/format'

function oneYearFromToday(): string {
  const date = new Date()
  date.setFullYear(date.getFullYear() + 1)
  return date.toISOString().slice(0, 10)
}

export function MemberDetailPage() {
  const { memberId } = useParams()
  const id = Number(memberId)

  const member = useMember(id)
  const loans = useLoans({ member: id, page_size: 50 })
  const update = useUpdateMember(id)
  const toast = useToast()

  const [reason, setReason] = useState('')

  if (member.isPending) return <RowsSkeleton rows={4} />
  if (member.isError) return <ErrorState error={member.error} onRetry={() => member.refetch()} />
  if (!member.data?.profile) return null

  const profile = member.data.profile

  const suspend = () => {
    update.mutate(
      { is_suspended: true, suspension_reason: reason.trim() || 'Suspended at the desk' },
      {
        onSuccess: () => {
          toast.success('Membership suspended.')
          setReason('')
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    )
  }

  const reinstate = () =>
    update.mutate(
      { is_suspended: false, suspension_reason: '' },
      {
        onSuccess: () => toast.success('Membership reinstated.'),
        onError: (error) => toast.error(errorMessage(error)),
      },
    )

  const extend = () =>
    update.mutate(
      { membership_expires_on: oneYearFromToday() },
      {
        onSuccess: () => toast.success('Membership extended by a year.'),
        onError: (error) => toast.error(errorMessage(error)),
      },
    )

  return (
    <>
      <Link
        to="/desk/members"
        className="text-sm text-ink/50 underline-offset-4 hover:text-ink hover:underline"
      >
        ← Members
      </Link>

      <PageHeading
        title={member.data.full_name}
        subtitle={member.data.email}
        actions={
          profile.is_suspended ? (
            <Badge tone="bad">Suspended</Badge>
          ) : profile.is_expired ? (
            <Badge tone="warn">Expired</Badge>
          ) : (
            <Badge tone="good">Active</Badge>
          )
        }
      />

      <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <section aria-labelledby="history-heading">
          <h2 id="history-heading" className="font-display text-xl font-semibold text-ink">
            Loan history
          </h2>

          <div className="mt-4 space-y-3">
            {loans.isPending && <RowsSkeleton rows={4} />}
            {loans.data?.results.length === 0 && (
              <EmptyState title="Nothing borrowed yet" description="This card has never been used." />
            )}
            {loans.data?.results.map((loan) => (
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
                <p className="text-sm text-ink/60">
                  {loan.returned_at
                    ? `Returned ${formatDate(loan.returned_at)}`
                    : `Due ${formatDate(loan.due_on)}`}
                </p>
                {loan.is_active && loan.is_overdue && (
                  <Badge tone="bad">
                    {loan.days_overdue} {pluralise(loan.days_overdue, 'day')} overdue
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </section>

        <aside className="space-y-6">
          <div className="rounded-sm border border-rule bg-white p-5">
            <h2 className="font-display text-lg font-semibold text-ink">Membership</h2>
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="field-label">Number</dt>
                <dd className="catalogue-data mt-1 text-ink">{profile.membership_number}</dd>
              </div>
              <div>
                <dt className="field-label">Joined</dt>
                <dd className="mt-1 text-ink/70">{formatDate(profile.joined_on)}</dd>
              </div>
              <div>
                <dt className="field-label">Expires</dt>
                <dd className="mt-1 text-ink/70">
                  {profile.membership_expires_on ? formatDate(profile.membership_expires_on) : 'No end date'}
                </dd>
              </div>
              {profile.phone && (
                <div>
                  <dt className="field-label">Phone</dt>
                  <dd className="catalogue-data mt-1">{profile.phone}</dd>
                </div>
              )}
              {profile.suspension_reason && (
                <div>
                  <dt className="field-label">Suspension reason</dt>
                  <dd className="mt-1 text-stamp">{profile.suspension_reason}</dd>
                </div>
              )}
            </dl>
          </div>

          <div className="rounded-sm border border-rule bg-white p-5">
            <h2 className="font-display text-lg font-semibold text-ink">Actions</h2>

            <div className="mt-4 space-y-3">
              <Button variant="secondary" className="w-full" onClick={extend} loading={update.isPending}>
                Extend by a year
              </Button>

              {profile.is_suspended ? (
                <Button className="w-full" onClick={reinstate} loading={update.isPending}>
                  Reinstate
                </Button>
              ) : (
                <div className="space-y-2">
                  <label htmlFor="suspend-reason" className="field-label">
                    Reason
                  </label>
                  <input
                    id="suspend-reason"
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    placeholder="Why suspend this card?"
                    className="field-input mt-0"
                  />
                  <Button
                    variant="danger"
                    className="w-full"
                    onClick={suspend}
                    loading={update.isPending}
                  >
                    Suspend
                  </Button>
                </div>
              )}
            </div>

            <p className="mt-4 text-xs text-ink/50">
              A suspended member keeps what they have out but cannot borrow or reserve again.
            </p>
          </div>
        </aside>
      </div>
    </>
  )
}
