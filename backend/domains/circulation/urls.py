from django.urls import path

from domains.circulation import views

urlpatterns = [
    path("loans", views.LoanListView.as_view(), name="loan-list"),
    path("loans/<int:loan_id>", views.LoanDetailView.as_view(), name="loan-detail"),
    path("loans/<int:loan_id>/return", views.LoanReturnView.as_view(), name="loan-return"),
    path("loans/<int:loan_id>/renew", views.LoanRenewView.as_view(), name="loan-renew"),
    path("reservations", views.ReservationListView.as_view(), name="reservation-list"),
    path(
        "reservations/<int:reservation_id>/cancel",
        views.ReservationCancelView.as_view(),
        name="reservation-cancel",
    ),
    path(
        "reservations/<int:reservation_id>/fulfil",
        views.ReservationFulfilView.as_view(),
        name="reservation-fulfil",
    ),
    path("fines", views.FineListView.as_view(), name="fine-list"),
    path("fines/<int:fine_id>/pay", views.FinePayView.as_view(), name="fine-pay"),
    path("fines/<int:fine_id>/waive", views.FineWaiveView.as_view(), name="fine-waive"),
    path("members/me/loans", views.MyLoansView.as_view(), name="my-loans"),
    path("members/me/reservations", views.MyReservationsView.as_view(), name="my-reservations"),
    path("members/me/fines", views.MyFinesView.as_view(), name="my-fines"),
    path("dashboard/stats", views.DashboardStatsView.as_view(), name="dashboard-stats"),
]
