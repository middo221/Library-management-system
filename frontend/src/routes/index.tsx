import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/AppShell'
import { ForbiddenPage, NotFoundPage } from '@/components/ErrorPages'
import { GuestOnlyRoute, ProtectedRoute, RoleRoute } from '@/features/auth/guards'
import { LoginPage } from '@/features/auth/LoginPage'
import { RegisterPage } from '@/features/auth/RegisterPage'
import { useAuthStore } from '@/features/auth/store'
import { BookDetailPage } from '@/features/catalog/BookDetailPage'
import { BookFormPage } from '@/features/catalog/BookFormPage'
import { CataloguePage } from '@/features/catalog/CataloguePage'
import { CopiesPage } from '@/features/catalog/CopiesPage'
import { CheckinPage } from '@/features/circulation/CheckinPage'
import { CheckoutPage } from '@/features/circulation/CheckoutPage'
import { DashboardPage } from '@/features/circulation/DashboardPage'
import { FinesPage } from '@/features/circulation/FinesPage'
import { HoldsPage } from '@/features/circulation/HoldsPage'
import { LoansPage } from '@/features/circulation/LoansPage'
import { MyShelfPage } from '@/features/circulation/MyShelfPage'
import { MemberDetailPage } from '@/features/members/MemberDetailPage'
import { MembersPage } from '@/features/members/MembersPage'

/**
 * The only thing in this directory: the route table.
 *
 * Pages live with the feature they belong to, so a change to circulation touches one folder
 * rather than three. URLs keep the /desk prefix for librarian screens because that is what
 * the people using them call it.
 */

/** Signed-in landing depends on which side of the desk you are on. */
function Home() {
  const user = useAuthStore((state) => state.user)
  return <Navigate to={user?.role === 'LIBRARIAN' ? '/desk' : '/catalogue'} replace />
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<GuestOnlyRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<Home />} />
          <Route path="/catalogue" element={<CataloguePage />} />
          <Route path="/catalogue/:bookId" element={<BookDetailPage />} />
          <Route path="/shelf" element={<MyShelfPage />} />
          <Route path="/no-access" element={<ForbiddenPage />} />

          <Route element={<RoleRoute role="LIBRARIAN" />}>
            <Route path="/desk" element={<DashboardPage />} />
            <Route path="/desk/checkout" element={<CheckoutPage />} />
            <Route path="/desk/checkin" element={<CheckinPage />} />
            <Route path="/desk/loans" element={<LoansPage />} />
            <Route path="/desk/holds" element={<HoldsPage />} />
            <Route path="/desk/fines" element={<FinesPage />} />
            <Route path="/desk/members" element={<MembersPage />} />
            <Route path="/desk/members/:memberId" element={<MemberDetailPage />} />
            <Route path="/desk/catalogue/new" element={<BookFormPage />} />
            <Route path="/desk/catalogue/:bookId/edit" element={<BookFormPage />} />
            <Route path="/desk/catalogue/:bookId/copies" element={<CopiesPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
