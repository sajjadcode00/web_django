from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("doctors/<int:doctor_id>/", views.create_appointment, name="create"),
    path("success/<int:appointment_id>/", views.appointment_success, name="success"),
    path("my-appointments/", views.patient_appointments, name="patient_appointments"),
    path("notifications/", views.patient_notifications, name="notifications"),
    path("notifications/<int:notification_id>/open/", views.open_patient_notification, name="open_notification"),
    path("my-appointments/<int:appointment_id>/cancel/", views.cancel_patient_appointment, name="cancel_patient_appointment"),
    path("doctor/", views.doctor_dashboard, name="doctor_dashboard"),
    path("doctor/schedule/", views.doctor_schedule, name="doctor_schedule"),
    path("doctor/schedule/<int:schedule_id>/delete/", views.delete_doctor_schedule, name="delete_doctor_schedule"),
    path("doctor/appointments/", views.doctor_appointments, name="doctor_appointments"),
    path("doctor/appointments/<int:appointment_id>/confirm/", views.confirm_doctor_appointment, name="confirm_doctor_appointment"),
    path("doctor/appointments/<int:appointment_id>/reject/", views.reject_doctor_appointment, name="reject_doctor_appointment"),
]
