from django.urls import path

from domains.accounts import views

urlpatterns = [
    path("members", views.MemberListView.as_view(), name="member-list"),
    path("members/<int:member_id>", views.MemberDetailView.as_view(), name="member-detail"),
]
