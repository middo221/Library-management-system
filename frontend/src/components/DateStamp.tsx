import { cn } from '@/lib/cn'
import { stampParts } from '@/lib/format'

interface DateStampProps {
  date: string
  overdue?: boolean
  label?: string
  className?: string
}

/**
 * The signature element: a due date rendered as an ink stamp on the card, slightly rotated,
 * stamp-red when overdue.
 *
 * It appears in exactly one place in the interface — on loan cards — which is what keeps it
 * memorable rather than decorative. Resist reusing it as a generic date badge.
 */
export function DateStamp({ date, overdue = false, label = 'Due', className }: DateStampProps) {
  const { day, month, year } = stampParts(date)

  return (
    <div
      className={cn(
        'inline-flex -rotate-3 select-none flex-col items-center rounded-[2px] border-2 px-3 py-1.5',
        'font-mono uppercase leading-none tracking-wider',
        overdue ? 'border-stamp text-stamp' : 'border-shelf/70 text-shelf',
        className,
      )}
    >
      <span className="text-[0.5rem] font-medium tracking-[0.2em] opacity-80">{label}</span>
      <span className="mt-1 text-lg font-medium">{day}</span>
      <span className="mt-0.5 text-[0.625rem] tracking-[0.15em]">{month}</span>
      <span className="mt-0.5 text-[0.5rem] tracking-[0.2em] opacity-70">{year}</span>
      <span className="sr-only">
        {label} {date}
        {overdue ? ' — overdue' : ''}
      </span>
    </div>
  )
}
