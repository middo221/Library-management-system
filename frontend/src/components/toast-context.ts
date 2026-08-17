import { createContext, useContext } from 'react'

export type ToastTone = 'success' | 'error' | 'info'

export interface ToastContextValue {
  notify: (message: string, tone?: ToastTone) => void
  success: (message: string) => void
  error: (message: string) => void
}

/** Kept apart from the provider component so fast refresh stays happy. */
export const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used inside a ToastProvider.')
  return context
}
