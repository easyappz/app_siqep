from django.urls import path

from .views import (
    HelloView,
    RegisterView,
    LoginView,
    MeView,
    ProfileStatsView,
    AdminMemberListCreateView,
    AdminMemberDetailView,
    AdminReferralEventListView,
    AdminStatsOverviewView,
)

urlpatterns = [
    path("hello/", HelloView.as_view(), name="hello"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("profile/stats/", ProfileStatsView.as_view(), name="profile-stats"),
    # Admin panel endpoints
    path(
        "admin/members/",
        AdminMemberListCreateView.as_view(),
        name="admin-members-list-create",
    ),
    path(
        "admin/members/<int:pk>/",
        AdminMemberDetailView.as_view(),
        name="admin-members-detail",
    ),
    path(
        "admin/referrals/",
        AdminReferralEventListView.as_view(),
        name="admin-referrals-list",
    ),
    path(
        "admin/stats/overview/",
        AdminStatsOverviewView.as_view(),
        name="admin-stats-overview",
    ),
]
