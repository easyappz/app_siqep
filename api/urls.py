from django.urls import path

from .views import (
    HelloView,
    RegisterView,
    LoginView,
    MeView,
    ProfileStatsView,
    ReferralTreeView,
    ReferralRewardsView,
    WithdrawalRequestListCreateView,
    AdminMemberListCreateView,
    AdminMemberDetailView,
    AdminReferralEventListView,
    AdminStatsOverviewView,
    TestSimulateDepositsView,
    SimulateDemoDepositsView,
)

urlpatterns = [
    path("hello/", HelloView.as_view(), name="hello"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("profile/stats/", ProfileStatsView.as_view(), name="profile-stats"),
    path(
        "referrals/tree/",
        ReferralTreeView.as_view(),
        name="referral-tree",
    ),
    path(
        "referrals/rewards/",
        ReferralRewardsView.as_view(),
        name="referral-rewards",
    ),
    path(
        "withdrawal-requests/",
        WithdrawalRequestListCreateView.as_view(),
        name="withdrawal-requests",
    ),
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
    # Test-only endpoints
    path(
        "test/simulate-deposits/",
        TestSimulateDepositsView.as_view(),
        name="test-simulate-deposits",
    ),
    path(
        "test/simulate_demo_deposits/",
        SimulateDemoDepositsView.as_view(),
        name="simulate-demo-deposits",
    ),
]
