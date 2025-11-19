from django.urls import path

from .views import HelloView, RegisterView, LoginView, MeView, ProfileStatsView

urlpatterns = [
    path("hello/", HelloView.as_view(), name="hello"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("profile/stats/", ProfileStatsView.as_view(), name="profile-stats"),
]
