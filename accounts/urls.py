from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import PatientAuthenticationForm
from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=PatientAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("register/", views.register, name="register"),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="accounts:login"),
        name="logout",
    ),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("doctors/", views.doctor_list, name="doctor_list"),
    path("doctors/<int:doctor_id>/", views.doctor_detail, name="doctor_detail"),
]
