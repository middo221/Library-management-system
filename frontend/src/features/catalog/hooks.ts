import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { catalogApi, type BookPayload, type BookQuery } from '@/api/endpoints'

export const catalogKeys = {
  all: ['catalog'] as const,
  books: (query: BookQuery) => [...catalogKeys.all, 'books', query] as const,
  book: (id: number) => [...catalogKeys.all, 'book', id] as const,
  copies: (bookId: number) => [...catalogKeys.all, 'copies', bookId] as const,
  categories: () => [...catalogKeys.all, 'categories'] as const,
  authors: (search: string) => [...catalogKeys.all, 'authors', search] as const,
}

export function useBooks(query: BookQuery) {
  return useQuery({
    queryKey: catalogKeys.books(query),
    queryFn: () => catalogApi.listBooks(query),
    // Keeps the previous page on screen while the next one loads, so typing in the search
    // box doesn't flash an empty grid on every keystroke.
    placeholderData: keepPreviousData,
  })
}

export function useBook(id: number) {
  return useQuery({
    queryKey: catalogKeys.book(id),
    queryFn: () => catalogApi.getBook(id),
    enabled: Number.isFinite(id),
  })
}

export function useCopies(bookId: number) {
  return useQuery({
    queryKey: catalogKeys.copies(bookId),
    queryFn: () => catalogApi.listCopies(bookId),
    enabled: Number.isFinite(bookId),
  })
}

export function useCategories() {
  return useQuery({
    queryKey: catalogKeys.categories(),
    queryFn: catalogApi.listCategories,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAuthors(search = '') {
  return useQuery({
    queryKey: catalogKeys.authors(search),
    queryFn: () => catalogApi.listAuthors({ search, page_size: 100 }),
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: BookPayload) => catalogApi.createBook(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: catalogKeys.all }),
  })
}

export function useUpdateBook(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Partial<BookPayload>) => catalogApi.updateBook(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: catalogKeys.all }),
  })
}

export function useDeleteBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => catalogApi.deleteBook(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: catalogKeys.all }),
  })
}

export function useAddCopy(bookId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: { barcode: string; call_number?: string }) =>
      catalogApi.addCopy(bookId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: catalogKeys.all }),
  })
}

export function useDeleteCopy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (copyId: number) => catalogApi.deleteCopy(copyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: catalogKeys.all }),
  })
}
