import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'
import type { CopyStatus, FineStatus, ReservationStatus } from '@/api/types'

type Tone = 'neutral' | 'good' | 'warn' | 'bad'

const TONES: Record<Tone, string> = {
  neutral: 'border-rule bg-white text-ink/70',
  good: 'border-shelf/30 bg-shelf/10 text-shelf',
  warn: 'border-brass/50 bg-brass/15 text-[#7A5F32]',
  bad: 'border-stamp/30 bg-stamp/10 text-stamp',
}

export function Badge({
  tone = 'neutral',
  children,
  className,
}: {
  tone?: Tone
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

const COPY_STATUS: Record<CopyStatus, { label: string; tone: Tone }> = {
  AVAILABLE: { label: 'On the shelf', tone: 'good' },
  ON_LOAN: { label: 'On loan', tone: 'neutral' },
  RESERVED: { label: 'Held', tone: 'warn' },
  LOST: { label: 'Lost', tone: 'bad' },
  DAMAGED: { label: 'Damaged', tone: 'bad' },
  WITHDRAWN: { label: 'Withdrawn', tone: 'neutral' },
}

export function CopyStatusBadge({ status }: { status: CopyStatus }) {
  const { label, tone } = COPY_STATUS[status]
  return <Badge tone={tone}>{label}</Badge>
}

const RESERVATION_STATUS: Record<ReservationStatus, { label: string; tone: Tone }> = {
  PENDING: { label: 'Waiting', tone: 'neutral' },
  READY: { label: 'Ready to collect', tone: 'good' },
  FULFILLED: { label: 'Collected', tone: 'neutral' },
  CANCELLED: { label: 'Cancelled', tone: 'neutral' },
  EXPIRED: { label: 'Expired', tone: 'neutral' },
}

export function ReservationStatusBadge({ status }: { status: ReservationStatus }) {
  const { label, tone } = RESERVATION_STATUS[status]
  return <Badge tone={tone}>{label}</Badge>
}

const FINE_STATUS: Record<FineStatus, { label: string; tone: Tone }> = {
  OUTSTANDING: { label: 'Owed', tone: 'bad' },
  PAID: { label: 'Paid', tone: 'good' },
  WAIVED: { label: 'Waived', tone: 'neutral' },
}

export function FineStatusBadge({ status }: { status: FineStatus }) {
  const { label, tone } = FINE_STATUS[status]
  return <Badge tone={tone}>{label}</Badge>
}

/** Availability on a catalogue row: the one number a browsing member actually wants. */
export function AvailabilityBadge({ available, total }: { available: number; total: number }) {
  if (total === 0) return <Badge tone="neutral">No copies</Badge>
  if (available === 0) return <Badge tone="warn">All {total} out</Badge>
  return (
    <Badge tone="good">
      {available} of {total} in
    </Badge>
  )
}
