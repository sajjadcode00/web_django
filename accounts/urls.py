from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.AccountLoginView.as_view(), name="login"),
    path("register/", views.register, name="register"),
    path("register/doctor/", views.doctor_register, name="doctor_register"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("doctors/", views.doctor_list, name="doctor_list"),
    path("doctors/<int:doctor_id>/", views.doctor_detail, name="doctor_detail"),
]
