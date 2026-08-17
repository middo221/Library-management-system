import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate } from 'react-router-dom'
import { z } from 'zod'

import { ApiError } from '@/api/errors'
import { Button } from '@/components/Button'
import { useRegister } from '@/features/auth/hooks'
import { useAuthStore } from '@/features/auth/store'
import { AuthLayout } from './AuthLayout'

const schema = z.object({
  first_name: z.string().max(80).optional(),
  last_name: z.string().max(80).optional(),
  email: z.string().min(1, 'Enter your email address.').email('That does not look like an email address.'),
  password: z.string().min(8, 'Use at least 8 characters.'),
  phone: z.string().max(32).optional(),
})

type FormValues = z.infer<typeof schema>

export function RegisterPage() {
  const register_ = useRegister()
  const user = useAuthStore((state) => state.user)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  // Field-level failures from the server land on the fields they belong to.
  useEffect(() => {
    if (!(register_.error instanceof ApiError)) return
    for (const [field, message] of Object.entries(register_.error.fieldErrors)) {
      if (field in schema.shape) setError(field as keyof FormValues, { message })
    }
  }, [register_.error, setError])

  if (user) return <Navigate to="/shelf" replace />

  return (
    <AuthLayout
      title="Join the library"
      subtitle="A membership number, and everything on the shelves."
      footer={
        <p className="text-sm text-ink/60">
          Already a member?{' '}
          <Link to="/login" className="font-medium text-shelf underline underline-offset-4">
            Sign in
          </Link>
        </p>
      }
    >
      <form
        onSubmit={handleSubmit((values) => register_.mutate(values))}
        className="space-y-5"
        noValidate
      >
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="first_name" className="field-label">
              First name
            </label>
            <input id="first_name" className="field-input" autoFocus {...register('first_name')} />
          </div>
          <div>
            <label htmlFor="last_name" className="field-label">
              Last name
            </label>
            <input id="last_name" className="field-input" {...register('last_name')} />
          </div>
        </div>

        <div>
          <label htmlFor="email" className="field-label">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
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
            autoComplete="new-password"
            className="field-input"
            aria-invalid={Boolean(errors.password)}
            {...register('password')}
          />
          {errors.password ? (
            <p className="field-error">{errors.password.message}</p>
          ) : (
            <p className="mt-1.5 text-xs text-ink/50">At least 8 characters, not all numbers.</p>
          )}
        </div>

        <div>
          <label htmlFor="phone" className="field-label">
            Phone <span className="normal-case tracking-normal text-ink/40">(optional)</span>
          </label>
          <input id="phone" className="field-input" {...register('phone')} />
        </div>

        {register_.isError && register_.error instanceof ApiError && !Object.keys(register_.error.fieldErrors).length && (
          <p role="alert" className="rounded-sm border border-stamp/30 bg-stamp/5 px-3 py-2.5 text-sm text-stamp">
            {register_.error.message}
          </p>
        )}

        <Button type="submit" loading={register_.isPending} className="w-full">
          {register_.isPending ? 'Joining' : 'Join the library'}
        </Button>
      </form>
    </AuthLayout>
  )
}
