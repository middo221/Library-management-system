import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'

import { cn } from '@/lib/cn'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  children: ReactNode
}

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-shelf text-paper hover:bg-shelf/90 disabled:bg-shelf/40',
  secondary: 'border border-rule bg-white text-ink hover:border-ink/40 disabled:text-ink/40',
  ghost: 'text-ink/70 hover:bg-ink/5 hover:text-ink disabled:text-ink/30',
  // stamp-red is reserved: destructive actions and overdue state, nothing else.
  danger: 'bg-stamp text-paper hover:bg-stamp/90 disabled:bg-stamp/40',
}

const SIZES: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2.5 text-sm',
}

/** Forwards its ref so keyboard-driven screens can move focus onto the confirm action. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading = false, disabled, className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      {...props}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-sm font-medium transition-colors',
        'disabled:cursor-not-allowed',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      )}
      {children}
    </button>
  )
})
