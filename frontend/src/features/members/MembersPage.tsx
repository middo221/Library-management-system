import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/Badge'
import { Pagination } from '@/components/Pagination'
import { EmptyState, ErrorState, PageHeading, RowsSkeleton } from '@/components/states'
import { useMembers } from '@/features/members/hooks'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { formatDate, formatMoney } from '@/lib/format'

export function MembersPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebouncedValue(search)
  const members = useMembers({ search: debouncedSearch || undefined, page })

  return (
    <>
      <PageHeading title="Members" subtitle="Who holds a card, and what they are holding." />

      <div className="mb-6 max-w-md">
        <label htmlFor="member-search" className="sr-only">
          Search members
        </label>
        <input
          id="member-search"
          type="search"
          value={search}
          onChange={(event) => {
            setPage(1)
            setSearch(event.target.value)
          }}
          placeholder="Name, email or membership number"
          className="field-input mt-0"
        />
      </div>

      {members.isPending && <RowsSkeleton rows={6} />}
      {members.isError && <ErrorState error={members.error} onRetry={() => members.refetch()} />}

      {members.data?.results.length === 0 && (
        <EmptyState
          title="No members match that"
          description="Membership numbers look like M-000142."
        />
      )}

      {members.data && members.data.results.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-sm border border-rule bg-white">
            <table className="w-full min-w-[44rem] text-left text-sm">
              <thead className="border-b border-rule text-xs uppercase tracking-[0.1em] text-ink/50">
                <tr>
                  <th className="px-4 py-3 font-semibold">Number</th>
                  <th className="px-4 py-3 font-semibold">Member</th>
                  <th className="px-4 py-3 font-semibold">On loan</th>
                  <th className="px-4 py-3 font-semibold">Owed</th>
                  <th className="px-4 py-3 font-semibold">Expires</th>
                  <th className="px-4 py-3 font-semibold">State</th>
                </tr>
              </thead>
              <tbody className="rule-divide">
                {members.data.results.map((member) => (
                  <tr key={member.id} className="transition-colors hover:bg-ink/[0.02]">
                    <td className="px-4 py-3">
                      <Link
                        to={`/desk/members/${member.id}`}
                        className="catalogue-data text-ink underline-offset-4 hover:underline"
                      >
                        {member.membership_number}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-ink">{member.full_name}</p>
                      <p className="text-xs text-ink/50">{member.email}</p>
                    </td>
                    <td className="px-4 py-3 text-ink/70">{member.active_loan_count}</td>
                    <td className="px-4 py-3">
                      {Number.parseFloat(member.unpaid_fine_total) > 0 ? (
                        <span className="font-mono text-stamp">
                          {formatMoney(member.unpaid_fine_total)}
                        </span>
                      ) : (
                        <span className="text-ink/40">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-ink/70">
                      {member.membership_expires_on ? formatDate(member.membership_expires_on) : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {member.is_suspended ? (
                        <Badge tone="bad">Suspended</Badge>
                      ) : member.is_active ? (
                        <Badge tone="good">Active</Badge>
                      ) : (
                        <Badge>Inactive</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination
            page={members.data.page}
            totalPages={members.data.total_pages}
            count={members.data.count}
            onChange={setPage}
            noun="member"
          />
        </>
      )}
    </>
  )
}
