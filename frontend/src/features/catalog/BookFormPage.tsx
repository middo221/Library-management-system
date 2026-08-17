import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate, useParams } from 'react-router-dom'
import { z } from 'zod'

import { ApiError, errorMessage } from '@/api/errors'
import { Button } from '@/components/Button'
import { useToast } from '@/components/toast-context'
import { ErrorState, PageHeading, RowsSkeleton } from '@/components/states'
import {
  useAuthors,
  useBook,
  useCategories,
  useCreateBook,
  useUpdateBook,
} from '@/features/catalog/hooks'

const schema = z.object({
  isbn: z.string().min(10, 'An ISBN is 10 or 13 digits.'),
  title: z.string().min(1, 'A title is required.'),
  subtitle: z.string().optional(),
  category_id: z.string().optional(),
  author_ids: z.array(z.string()).optional(),
  publisher: z.string().optional(),
  published_year: z.string().optional(),
  language: z.string().optional(),
  page_count: z.string().optional(),
  description: z.string().optional(),
  cover_url: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

function toPayload(values: FormValues) {
  return {
    isbn: values.isbn.trim(),
    title: values.title.trim(),
    subtitle: values.subtitle?.trim() ?? '',
    category_id: values.category_id ? Number(values.category_id) : null,
    author_ids: (values.author_ids ?? []).map(Number),
    publisher: values.publisher?.trim() ?? '',
    published_year: values.published_year ? Number(values.published_year) : null,
    language: values.language?.trim() || 'English',
    page_count: values.page_count ? Number(values.page_count) : null,
    description: values.description?.trim() ?? '',
    cover_url: values.cover_url?.trim() ?? '',
  }
}

export function BookFormPage() {
  const { bookId } = useParams()
  const id = bookId ? Number(bookId) : undefined
  const isEdit = id !== undefined

  const navigate = useNavigate()
  const toast = useToast()

  const existing = useBook(id ?? Number.NaN)
  const categories = useCategories()
  const authors = useAuthors()
  const create = useCreateBook()
  const update = useUpdateBook(id ?? 0)
  const mutation = isEdit ? update : create

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { language: 'English' } })

  useEffect(() => {
    if (!isEdit || !existing.data) return
    reset({
      isbn: existing.data.isbn,
      title: existing.data.title,
      subtitle: existing.data.subtitle,
      category_id: existing.data.category ? String(existing.data.category.id) : '',
      author_ids: existing.data.authors.map((author) => String(author.id)),
      publisher: existing.data.publisher,
      published_year: existing.data.published_year ? String(existing.data.published_year) : '',
      language: existing.data.language,
      page_count: existing.data.page_count ? String(existing.data.page_count) : '',
      description: existing.data.description,
      cover_url: existing.data.cover_url,
    })
  }, [isEdit, existing.data, reset])

  useEffect(() => {
    if (!(mutation.error instanceof ApiError)) return
    for (const [field, message] of Object.entries(mutation.error.fieldErrors)) {
      if (field in schema.shape) setError(field as keyof FormValues, { message })
    }
  }, [mutation.error, setError])

  if (isEdit && existing.isPending) return <RowsSkeleton rows={5} />
  if (isEdit && existing.isError) return <ErrorState error={existing.error} />

  const onSubmit = handleSubmit((values) => {
    mutation.mutate(toPayload(values), {
      onSuccess: (book) => {
        toast.success(isEdit ? 'Record updated.' : 'Added to the catalogue.')
        navigate(`/catalogue/${book.id}`)
      },
      onError: (error) => toast.error(errorMessage(error)),
    })
  })

  return (
    <>
      <PageHeading
        title={isEdit ? 'Edit record' : 'New title'}
        subtitle="The bibliographic record. Physical copies are added separately."
      />

      <form onSubmit={onSubmit} className="max-w-3xl space-y-6" noValidate>
        <div className="rounded-sm border border-rule bg-white p-5">
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label htmlFor="title" className="field-label">
                Title
              </label>
              <input id="title" className="field-input" autoFocus {...register('title')} />
              {errors.title && <p className="field-error">{errors.title.message}</p>}
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="subtitle" className="field-label">
                Subtitle
              </label>
              <input id="subtitle" className="field-input" {...register('subtitle')} />
            </div>

            <div>
              <label htmlFor="isbn" className="field-label">
                ISBN
              </label>
              <input id="isbn" className="field-input font-mono" {...register('isbn')} />
              {errors.isbn && <p className="field-error">{errors.isbn.message}</p>}
            </div>

            <div>
              <label htmlFor="category_id" className="field-label">
                Category
              </label>
              <select id="category_id" className="field-input" {...register('category_id')}>
                <option value="">Uncategorised</option>
                {categories.data?.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="author_ids" className="field-label">
                Authors <span className="normal-case tracking-normal text-ink/40">(ctrl-click for several)</span>
              </label>
              <select
                id="author_ids"
                multiple
                size={6}
                className="field-input"
                {...register('author_ids')}
              >
                {authors.data?.results.map((author) => (
                  <option key={author.id} value={author.id}>
                    {author.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="publisher" className="field-label">
                Publisher
              </label>
              <input id="publisher" className="field-input" {...register('publisher')} />
            </div>

            <div>
              <label htmlFor="published_year" className="field-label">
                Published
              </label>
              <input
                id="published_year"
                type="number"
                className="field-input"
                {...register('published_year')}
              />
            </div>

            <div>
              <label htmlFor="language" className="field-label">
                Language
              </label>
              <input id="language" className="field-input" {...register('language')} />
            </div>

            <div>
              <label htmlFor="page_count" className="field-label">
                Pages
              </label>
              <input
                id="page_count"
                type="number"
                className="field-input"
                {...register('page_count')}
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="description" className="field-label">
                Description
              </label>
              <textarea id="description" rows={4} className="field-input" {...register('description')} />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <Button type="submit" loading={mutation.isPending}>
            {isEdit ? 'Save changes' : 'Add to catalogue'}
          </Button>
          <Button type="button" variant="ghost" onClick={() => navigate(-1)}>
            Cancel
          </Button>
        </div>
      </form>
    </>
  )
}
