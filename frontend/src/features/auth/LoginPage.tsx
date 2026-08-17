import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { z } from 'zod'

import { ApiError } from '@/api/errors'
import { Button } from '@/components/Button'
import { useLogin } from '@/features/auth/hooks'
import { useAuthStore } from '@/features/auth/store'
import { AuthLayout } from './AuthLayout'

const schema = z.object({
  email: z.string().min(1, 'Enter your email address.').email('That does not look like an email address.'),
  password: z.string().min(1, 'Enter your password.'),
})

type FormValues = z.infer<typeof schema>

export function LoginPage() {
  const login = useLogin()
  const user = useAuthStore((state) => state.user)
  const location = useLocation()
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  if (user) {
    return <Navigate to={from ?? (user.role === 'LIBRARIAN' ? '/desk' : '/shelf')} replace />
  }

  return (
    <AuthLayout
      title="Sign in"
      subtitle="Your membership number and loans are behind this door."
      footer={
        <p className="text-sm text-ink/60">
          No account yet?{' '}
          <Link to="/register" className="font-medium text-shelf underline underline-offset-4">
            Join the library
          </Link>
        </p>
      }
    >
      <form
        onSubmit={handleSubmit((values) => login.mutate(values))}
        className="space-y-5"
        noValidate
      >
        <div>
          <label htmlFor="email" className="field-label">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            autoFocus
            className="field-input"
            aria-invalid={Boolean(errors.email)}
            {...register('email')}
          />
          {errors.email && <p className="field-error">{errors.email.message}</p>}
        </div>

        <div>
          <label htmlFor="password" className="field-label">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className="field-input"
            aria-invalid={Boolean(errors.password)}
            {...register('password')}
          />
          {errors.password && <p className="field-error">{errors.password.message}</p>}
        </div>

        {login.isError && (
          <p role="alert" className="rounded-sm border border-stamp/30 bg-stamp/5 px-3 py-2.5 text-sm text-stamp">
            {login.error instanceof ApiError ? login.error.message : 'Sign in failed. Try again.'}
          </p>
        )}

        <Button type="submit" loading={login.isPending} className="w-full">
          {login.isPending ? 'Signing in' : 'Sign in'}
        </Button>
      </form>
    </AuthLayout>
  )
}
