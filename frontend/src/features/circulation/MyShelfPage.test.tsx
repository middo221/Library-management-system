import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MockAdapter from 'axios-mock-adapter'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { api } from '@/api/client'
import { ToastProvider } from '@/components/Toast'
import { MyShelfPage } from './MyShelfPage'

let mock: MockAdapter

const OVERDUE_LOAN = {
  id: 1,
  book: { id: 7, title: 'Invisible Cities', isbn: '9780156453806', cover_url: '', authors: ['Italo Calvino'] },
  copy: { id: 3, barcode: 'L00701', call_number: '853.914 CAL', status: 'ON_LOAN' },
  member: { id: 2, email: 'rosa@x.test', full_name: 'Rosa Quill', membership_number: 'M-000001' },
  checked_out_at: '2026-01-01T10:00:00Z',
  due_on: '2026-01-15',
  returned_at: null,
  renewal_count: 0,
  is_active: true,
  is_overdue: true,
  days_overdue: 4,
}

const HEALTHY_LOAN = { ...OVERDUE_LOAN, id: 2, is_overdue: false, days_overdue: 0, due_on: '2099-01-15' }

function page<T>(results: T[]) {
  return { count: results.length, page: 1, page_size: 20, total_pages: 1, next: null, previous: null, results }
}

function renderShelf() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter>
          <MyShelfPage />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  mock = new MockAdapter(api)
  mock.onGet('/members/me/reservations').reply(200, page([]))
  mock.onGet('/members/me/fines').reply(200, page([]))
})

afterEach(() => mock.restore())

describe('My shelf', () => {
  it('shows an inviting empty state when nothing is out', async () => {
    mock.onGet('/members/me/loans').reply(200, page([]))

    renderShelf()

    expect(await screen.findByText('No loans yet')).toBeInTheDocument()
    expect(screen.getByText(/Browse the catalogue to get started/i)).toBeInTheDocument()
  })

  it('marks an overdue loan and blocks renewal with a reason', async () => {
    mock.onGet('/members/me/loans').reply(200, page([OVERDUE_LOAN]))

    renderShelf()

    expect(await screen.findByText('Invisible Cities')).toBeInTheDocument()
    expect(screen.getByText('4 days overdue')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Renew' })).toBeDisabled()
    expect(screen.getByText('Overdue loans are renewed at the desk.')).toBeInTheDocument()
  })

  it('renews a healthy loan and surfaces the new due date', async () => {
    mock.onGet('/members/me/loans').reply(200, page([HEALTHY_LOAN]))
    mock.onPost('/loans/2/renew').reply(200, { ...HEALTHY_LOAN, due_on: '2099-01-29', renewal_count: 1 })

    renderShelf()

    const renew = await screen.findByRole('button', { name: 'Renew' })
    await userEvent.click(renew)

    await waitFor(() => {
      expect(screen.getByText(/Renewed — now due 29 Jan 2099/)).toBeInTheDocument()
    })
  })

  it("surfaces the server's own message when a renewal is refused", async () => {
    mock.onGet('/members/me/loans').reply(200, page([HEALTHY_LOAN]))
    mock.onPost('/loans/2/renew').reply(409, {
      error: {
        code: 'RENEWAL_BLOCKED_RESERVED',
        message: 'Another member is waiting for this title, so it cannot be renewed.',
        details: {},
      },
    })

    renderShelf()

    await userEvent.click(await screen.findByRole('button', { name: 'Renew' }))

    await waitFor(() => {
      expect(
        screen.getByText('Another member is waiting for this title, so it cannot be renewed.'),
      ).toBeInTheDocument()
    })
  })
})
