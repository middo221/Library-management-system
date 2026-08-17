/**
 * Every network call the app makes, in one module.
 *
 * Components never touch `api` directly; they go through hooks, which go through here. That
 * keeps the URL surface auditable against the OpenAPI schema.
 */

import { api } from './client'
import type {
  AuthResponse,
  Author,
  Book,
  BookCopy,
  BookListItem,
  Category,
  CheckinResult,
  DashboardStats,
  Fine,
  Loan,
  MemberListItem,
  Paginated,
  Reservation,
  User,
} from './types'

// ------------------------------------------------------------------------------- auth ---

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload extends LoginPayload {
  first_name?: string
  last_name?: string
  phone?: string
  address?: string
}

export const authApi = {
  login: (payload: LoginPayload) =>
    api.post<AuthResponse>('/auth/login', payload).then((r) => r.data),
  register: (payload: RegisterPayload) =>
    api.post<AuthResponse>('/auth/register', payload).then((r) => r.data),
  logout: (refresh: string) => api.post('/auth/logout', { refresh }).then((r) => r.data),
  me: () => api.get<User>('/auth/me').then((r) => r.data),
  updateMe: (payload: Partial<Pick<User, 'first_name' | 'last_name'>> & { phone?: string; address?: string }) =>
    api.patch<User>('/auth/me', payload).then((r) => r.data),
  changePassword: (payload: { current_password: string; new_password: string }) =>
    api.post('/auth/change-password', payload).then((r) => r.data),
}

// ---------------------------------------------------------------------------- catalog ---

export interface BookQuery {
  search?: string
  category?: number
  author?: number
  language?: string
  available?: boolean
  ordering?: string
  page?: number
  page_size?: number
}

export interface BookPayload {
  isbn: string
  title: string
  subtitle?: string
  author_ids?: number[]
  category_id?: number | null
  publisher?: string
  published_year?: number | null
  language?: string
  page_count?: number | null
  description?: string
  cover_url?: string
}

export const catalogApi = {
  listBooks: (params: BookQuery) =>
    api.get<Paginated<BookListItem>>('/books', { params }).then((r) => r.data),
  getBook: (id: number) => api.get<Book>(`/books/${id}`).then((r) => r.data),
  createBook: (payload: BookPayload) => api.post<Book>('/books', payload).then((r) => r.data),
  updateBook: (id: number, payload: Partial<BookPayload>) =>
    api.patch<Book>(`/books/${id}`, payload).then((r) => r.data),
  deleteBook: (id: number) => api.delete(`/books/${id}`).then(() => undefined),

  listCopies: (bookId: number) =>
    api.get<BookCopy[]>(`/books/${bookId}/copies`).then((r) => r.data),
  addCopy: (bookId: number, payload: { barcode: string; call_number?: string; replacement_cost?: string }) =>
    api.post<BookCopy>(`/books/${bookId}/copies`, payload).then((r) => r.data),
  updateCopy: (copyId: number, payload: Partial<Pick<BookCopy, 'call_number' | 'status' | 'condition_note'>>) =>
    api.patch<BookCopy>(`/copies/${copyId}`, payload).then((r) => r.data),
  deleteCopy: (copyId: number) => api.delete(`/copies/${copyId}`).then(() => undefined),

  listAuthors: (params: { search?: string; page_size?: number } = {}) =>
    api.get<Paginated<Author>>('/authors', { params }).then((r) => r.data),
  createAuthor: (payload: { name: string; bio?: string }) =>
    api.post<Author>('/authors', payload).then((r) => r.data),

  listCategories: () => api.get<Category[]>('/categories').then((r) => r.data),
  createCategory: (payload: { name: string; description?: string }) =>
    api.post<Category>('/categories', payload).then((r) => r.data),
}

// ------------------------------------------------------------------------ circulation ---

export interface LoanQuery {
  status?: 'active' | 'overdue' | 'returned' | ''
  member?: number
  book?: number
  search?: string
  page?: number
  page_size?: number
}

export const circulationApi = {
  listLoans: (params: LoanQuery = {}) =>
    api.get<Paginated<Loan>>('/loans', { params }).then((r) => r.data),
  getLoan: (id: number) => api.get<Loan>(`/loans/${id}`).then((r) => r.data),
  checkout: (payload: { barcode: string; member_id: number }) =>
    api.post<Loan>('/loans', payload).then((r) => r.data),
  checkin: (loanId: number) =>
    api.post<CheckinResult>(`/loans/${loanId}/return`).then((r) => r.data),
  renew: (loanId: number) => api.post<Loan>(`/loans/${loanId}/renew`).then((r) => r.data),

  listReservations: (params: { status?: string; book?: number; member?: number } = {}) =>
    api.get<Paginated<Reservation>>('/reservations', { params }).then((r) => r.data),
  reserve: (payload: { book_id: number; member_id?: number }) =>
    api.post<Reservation>('/reservations', payload).then((r) => r.data),
  cancelReservation: (id: number) =>
    api.post<Reservation>(`/reservations/${id}/cancel`).then((r) => r.data),
  fulfilReservation: (id: number) =>
    api.post<Loan>(`/reservations/${id}/fulfil`).then((r) => r.data),

  listFines: (params: { status?: string; member?: number } = {}) =>
    api.get<Paginated<Fine>>('/fines', { params }).then((r) => r.data),
  payFine: (id: number) => api.post<Fine>(`/fines/${id}/pay`).then((r) => r.data),
  waiveFine: (id: number, reason: string) =>
    api.post<Fine>(`/fines/${id}/waive`, { reason }).then((r) => r.data),

  myLoans: (params: { status?: string } = {}) =>
    api.get<Paginated<Loan>>('/members/me/loans', { params }).then((r) => r.data),
  myReservations: () =>
    api.get<Paginated<Reservation>>('/members/me/reservations').then((r) => r.data),
  myFines: () => api.get<Paginated<Fine>>('/members/me/fines').then((r) => r.data),

  dashboardStats: () => api.get<DashboardStats>('/dashboard/stats').then((r) => r.data),
}

// ---------------------------------------------------------------------------- members ---

export const membersApi = {
  list: (params: { search?: string; is_suspended?: boolean; page?: number } = {}) =>
    api.get<Paginated<MemberListItem>>('/members', { params }).then((r) => r.data),
  get: (id: number) => api.get<User>(`/members/${id}`).then((r) => r.data),
  update: (
    id: number,
    payload: {
      is_suspended?: boolean
      suspension_reason?: string
      membership_expires_on?: string | null
      is_active?: boolean
    },
  ) => api.patch<User>(`/members/${id}`, payload).then((r) => r.data),
}
