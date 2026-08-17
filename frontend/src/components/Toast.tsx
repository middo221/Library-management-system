import { useCallback, useMemo, useState, type ReactNode } from 'react'

import { cn } from '@/lib/cn'
import { ToastContext, type ToastContextValue, type ToastTone } from './toast-context'

interface Toast {
  id: number
  tone: ToastTone
  message: string
}

const TONE_STYLES: Record<ToastTone, string> = {
  success: 'border-shelf/40 bg-shelf text-paper',
  error: 'border-stamp/40 bg-stamp text-paper',
  info: 'border-rule bg-ink text-paper',
}

let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const notify = useCallback(
    (message: string, tone: ToastTone = 'info') => {
      const id = nextId++
      setToasts((current) => [...current, { id, tone, message }])
      window.setTimeout(() => dismiss(id), 5000)
    },
    [dismiss],
  )

  const value = useMemo<ToastContextValue>(
    () => ({
      notify,
      success: (message: string) => notify(message, 'success'),
      error: (message: string) => notify(message, 'error'),
    }),
    [notify],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4 sm:items-end"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={cn(
              'pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-sm border px-4 py-3 text-sm shadow-lg',
              'animate-reveal-up',
              TONE_STYLES[toast.tone],
            )}
          >
            <span className="flex-1">{toast.message}</span>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="shrink-0 opacity-70 transition-opacity hover:opacity-100"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
