import { Button } from './Button'

interface PaginationProps {
  page: number
  totalPages: number
  count: number
  onChange: (page: number) => void
  noun?: string
}

export function Pagination({ page, totalPages, count, onChange, noun = 'result' }: PaginationProps) {
  if (totalPages <= 1) {
    return (
      <p className="mt-6 text-sm text-ink/50">
        {count} {noun}
        {count === 1 ? '' : 's'}
      </p>
    )
  }

  return (
    <nav
      className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-rule pt-5"
      aria-label="Pagination"
    >
      <p className="text-sm text-ink/50">
        Page <span className="catalogue-data">{page}</span> of{' '}
        <span className="catalogue-data">{totalPages}</span> · {count} {noun}
        {count === 1 ? '' : 's'}
      </p>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          Previous
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
        >
          Next
        </Button>
      </div>
    </nav>
  )
}
