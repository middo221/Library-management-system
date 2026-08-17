/** Formatting helpers. Dates are rendered in the library's voice, not the browser's. */

const DATE_FORMAT = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

const DATE_TIME_FORMAT = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  return DATE_FORMAT.format(new Date(value))
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return DATE_TIME_FORMAT.format(new Date(value))
}

export function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '£0.00'
  const amount = typeof value === 'string' ? Number.parseFloat(value) : value
  if (Number.isNaN(amount)) return '£0.00'
  return `£${amount.toFixed(2)}`
}

/** "Due in 3 days" / "6 days overdue" — the phrasing a person would actually use. */
export function describeDueDate(dueOn: string, isOverdue: boolean, daysOverdue: number): string {
  if (isOverdue) return daysOverdue === 1 ? '1 day overdue' : `${daysOverdue} days overdue`

  const due = new Date(`${dueOn}T00:00:00`)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const days = Math.round((due.getTime() - today.getTime()) / 86_400_000)

  if (days <= 0) return 'Due today'
  if (days === 1) return 'Due tomorrow'
  return `Due in ${days} days`
}

/** The three parts of a date stamp: 14 / MAR / 2026. */
export function stampParts(value: string): { day: string; month: string; year: string } {
  const date = new Date(`${value}T00:00:00`)
  return {
    day: String(date.getDate()).padStart(2, '0'),
    month: date.toLocaleString('en-GB', { month: 'short' }).toUpperCase(),
    year: String(date.getFullYear()),
  }
}

export function pluralise(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : (plural ?? `${singular}s`)
}
