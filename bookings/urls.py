from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("doctors/<int:doctor_id>/", views.create_appointment, name="create"),
    path("success/<int:appointment_id>/", views.appointment_success, name="success"),
]
