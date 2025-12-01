from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_view, name="accounts-register"),
    path("login/", views.login_view, name="accounts-login"),
    path("logout/", views.logout_view, name="accounts-logout"),
    path("profile/", views.profile_view, name="accounts-profile"),
]
