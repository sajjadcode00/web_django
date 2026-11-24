from django.contrib import admin

from .models import Appointment, DoctorSchedule


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient_name",
        "doctor_name",
        "appointment_date",
        "appointment_time",
        "status",
        "created_at",
    )
    list_filter = ("status", "appointment_date")
    search_fields = (
        "patient__user__first_name",
        "patient__user__last_name",
        "patient__user__username",
        "doctor__user__first_name",
        "doctor__user__last_name",
        "doctor__user__username",
    )
    date_hierarchy = "appointment_date"
    readonly_fields = ("created_at",)
    list_select_related = ("patient__user", "doctor__user")

    @admin.display(description="بیمار")
    def patient_name(self, obj):
        return obj.patient.user.get_full_name() or obj.patient.user.username

    @admin.display(description="پزشک")
    def doctor_name(self, obj):
        return obj.doctor.user.get_full_name() or obj.doctor.user.username


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ("doctor", "weekday", "start_time", "end_time", "slot_duration_minutes", "is_active")
    list_filter = ("weekday", "is_active")
    search_fields = ("doctor__user__first_name", "doctor__user__last_name", "doctor__user__username")
    list_select_related = ("doctor__user",)
