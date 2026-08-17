import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

import { ApiError } from '@/api/errors'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ToastProvider } from '@/components/Toast'
import { useSessionBootstrap, useSessionExpiryListener } from '@/features/auth/hooks'
import { AppRoutes } from '@/routes'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // Retrying a 4xx just repeats the same answer more slowly.
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false
        return failureCount < 2
      },
    },
  },
})

function Session({ children }: { children: React.ReactNode }) {
  useSessionBootstrap()
  useSessionExpiryListener()
  return <>{children}</>
}

export function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <BrowserRouter>
            <Session>
              <AppRoutes />
            </Session>
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
