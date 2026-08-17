import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import type { BookListItem } from '@/api/types'
import { AvailabilityBadge } from '@/components/Badge'
import { Pagination } from '@/components/Pagination'
import { CardsSkeleton, EmptyState, ErrorState, PageHeading } from '@/components/states'
import { useBooks, useCategories } from '@/features/catalog/hooks'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'

function BookCard({ book, index }: { book: BookListItem; index: number }) {
  return (
    <Link
      to={`/catalogue/${book.id}`}
      style={{ animationDelay: `${Math.min(index, 11) * 35}ms` }}
      className="group flex animate-reveal-up flex-col rounded-sm border border-rule bg-white p-5 transition-colors hover:border-ink/30"
    >
      <div className="flex items-start justify-between gap-3">
        <span className="catalogue-data">{book.isbn}</span>
        <AvailabilityBadge available={book.available_copies} total={book.total_copies} />
      </div>

      <h2 className="mt-4 font-display text-lg font-semibold leading-snug text-ink group-hover:text-shelf">
        {book.title}
      </h2>
      {book.subtitle && <p className="mt-1 text-sm text-ink/50">{book.subtitle}</p>}

      <p className="mt-3 text-sm text-ink/70">
        {book.authors.length ? book.authors.map((author) => author.name).join(', ') : 'Unattributed'}
      </p>

      <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 pt-5 text-xs text-ink/45">
        {book.category && <span>{book.category.name}</span>}
        {book.published_year && <span>{book.published_year}</span>}
        <span>{book.language}</span>
      </div>
    </Link>
  )
}

export function CataloguePage() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<number | undefined>()
  const [availableOnly, setAvailableOnly] = useState(false)
  const [page, setPage] = useState(1)

  const debouncedSearch = useDebouncedValue(search)
  const categories = useCategories()

  // Any filter change starts a new result set; staying on page 7 of the old one is a bug.
  useEffect(() => setPage(1), [debouncedSearch, category, availableOnly])

  const books = useBooks({
    search: debouncedSearch || undefined,
    category,
    available: availableOnly || undefined,
    page,
    page_size: 12,
  })

  return (
    <>
      <PageHeading
        title="Catalogue"
        subtitle="Everything the library holds, and what is on the shelf right now."
      />

      <div className="mb-8 flex flex-wrap items-end gap-4">
        <div className="min-w-[16rem] flex-1">
          <label htmlFor="catalogue-search" className="field-label">
            Search
          </label>
          <input
            id="catalogue-search"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Title, ISBN or author"
            className="field-input"
          />
        </div>

        <div className="w-56">
          <label htmlFor="catalogue-category" className="field-label">
            Category
          </label>
          <select
            id="catalogue-category"
            value={category ?? ''}
            onChange={(event) => setCategory(event.target.value ? Number(event.target.value) : undefined)}
            className="field-input"
          >
            <option value="">All categories</option>
            {categories.data?.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 pb-2.5 text-sm text-ink/70">
          <input
            type="checkbox"
            checked={availableOnly}
            onChange={(event) => setAvailableOnly(event.target.checked)}
            className="h-4 w-4 rounded-sm border-rule text-shelf focus:ring-shelf"
          />
          On the shelf only
        </label>
      </div>

      {books.isPending && <CardsSkeleton />}
      {books.isError && <ErrorState error={books.error} onRetry={() => books.refetch()} />}

      {books.data && books.data.results.length === 0 && (
        <EmptyState
          title="Nothing matches that"
          description="Try a shorter search, a different category, or clear the availability filter."
        />
      )}

      {books.data && books.data.results.length > 0 && (
        <>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {books.data.results.map((book, index) => (
              <BookCard key={book.id} book={book} index={index} />
            ))}
          </div>
          <Pagination
            page={books.data.page}
            totalPages={books.data.total_pages}
            count={books.data.count}
            onChange={setPage}
            noun="title"
          />
        </>
      )}
    </>
  )
}
