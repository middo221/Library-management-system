/**
 * Hand-written mirrors of the backend DTOs.
 *
 * `schema.d.ts` is generated from `openapi.json` (`npm run schema`) and is the source of
 * truth for the wire format; these aliases are what the app imports so a schema regeneration
 * shows up as type errors in one file rather than three hundred.
 */

export type Role = 'LIBRARIAN' | 'MEMBER'

export type CopyStatus =
  | 'AVAILABLE'
  | 'ON_LOAN'
  | 'RESERVED'
  | 'LOST'
  | 'DAMAGED'
  | 'WITHDRAWN'

export type ReservationStatus = 'PENDING' | 'READY' | 'FULFILLED' | 'CANCELLED' | 'EXPIRED'

export type FineStatus = 'OUTSTANDING' | 'PAID' | 'WAIVED'

export type FineReason = 'OVERDUE' | 'DAMAGE' | 'LOST'

export interface Paginated<T> {
  count: number
  page: number
  page_size: number
  total_pages: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface MemberProfile {
  membership_number: string
  phone: string
  address: string
  joined_on: string
  membership_expires_on: string | null
  is_suspended: boolean
  suspension_reason: string
  is_expired: boolean
  can_borrow: boolean
}

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: Role
  is_active: boolean
  date_joined: string
  profile: MemberProfile | null
}

export interface MemberListItem {
  id: number
  email: string
  full_name: string
  membership_number: string
  is_active: boolean
  is_suspended: boolean
  membership_expires_on: string | null
  active_loan_count: number
  unpaid_fine_total: string
}

export interface TokenPair {
  access: string
  refresh: string
}

export interface AuthResponse extends TokenPair {
  user: User
}

export interface AuthorSummary {
  id: number
  name: string
}

export interface Author extends AuthorSummary {
  bio: string
  birth_year: number | null
  death_year: number | null
  book_count?: number
}

export interface CategorySummary {
  id: number
  name: string
  slug: string
}

export interface Category extends CategorySummary {
  description: string
  book_count?: number
}

export interface BookListItem {
  id: number
  isbn: string
  title: string
  subtitle: string
  authors: AuthorSummary[]
  category: CategorySummary | null
  published_year: number | null
  language: string
  cover_url: string
  total_copies: number
  available_copies: number
}

export interface Book extends BookListItem {
  publisher: string
  page_count: number | null
  description: string
  created_at: string
}

export interface BookCopy {
  id: number
  book_id: number
  book_title: string
  barcode: string
  call_number: string
  status: CopyStatus
  acquired_on: string
  condition_note: string
  replacement_cost: string | null
}

export interface CopySummary {
  id: number
  barcode: string
  call_number: string
  status: CopyStatus
}

export interface BookSummary {
  id: number
  title: string
  isbn: string
  cover_url: string
  authors: string[]
}

export interface MemberSummary {
  id: number
  email: string
  full_name: string
  membership_number: string
}

export interface Loan {
  id: number
  book: BookSummary
  copy: CopySummary
  member: MemberSummary
  checked_out_at: string
  due_on: string
  returned_at: string | null
  renewal_count: number
  is_active: boolean
  is_overdue: boolean
  days_overdue: number
}

export interface Reservation {
  id: number
  book: BookSummary
  member: MemberSummary
  status: ReservationStatus
  reserved_at: string
  ready_at: string | null
  expires_on: string | null
  queue_position: number
  held_copy: CopySummary | null
}

export interface Fine {
  id: number
  loan_id: number
  member: MemberSummary
  book_title: string
  amount: string
  reason: FineReason
  status: FineStatus
  assessed_on: string
  paid_at: string | null
  waived_at: string | null
  waiver_reason: string
}

export interface CheckinResult {
  loan: Loan
  fine: Fine | null
  hold: Reservation | null
  copy_status: CopyStatus
  message: string
}

export interface DashboardStats {
  total_titles: number
  total_copies: number
  copies_available: number
  copies_on_loan: number
  loans_active: number
  loans_overdue: number
  loans_due_today: number
  active_members: number
  suspended_members: number
  reservations_waiting: number
  reservations_ready: number
  unpaid_fines_total: string
  unpaid_fines_count: number
}

/** The one error shape the backend ever returns. */
export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
    details: Record<string, unknown>
  }
}
