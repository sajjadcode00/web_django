from django.contrib import admin
from django.contrib.auth.models import User

from .models import Doctor, Patient


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("doctor_name", "specialty", "medical_system_number", "clinic", "account_active")
    list_filter = ("user__is_active", "specialty", "clinic")
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__username",
        "medical_system_number",
    )
    list_select_related = ("user", "clinic")
    actions = ("activate_doctor_accounts", "deactivate_doctor_accounts")

    @admin.display(description="نام پزشک")
    def doctor_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(boolean=True, description="حساب فعال")
    def account_active(self, obj):
        return obj.user.is_active

    @admin.action(description="تأیید و فعال‌سازی حساب پزشکان انتخاب‌شده")
    def activate_doctor_accounts(self, request, queryset):
        user_ids = queryset.values_list("user_id", flat=True)
        updated = User.objects.filter(pk__in=user_ids).update(is_active=True)
        self.message_user(request, f"تعداد {updated} حساب پزشک فعال شد.")

    @admin.action(description="غیرفعال‌سازی حساب پزشکان انتخاب‌شده")
    def deactivate_doctor_accounts(self, request, queryset):
        user_ids = queryset.values_list("user_id", flat=True)
        updated = User.objects.filter(pk__in=user_ids).update(is_active=False)
        self.message_user(request, f"تعداد {updated} حساب پزشک غیرفعال شد.")


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("patient_name", "national_id", "phone_number")
    search_fields = ("user__first_name", "user__last_name", "user__username", "national_id", "phone_number")
    list_select_related = ("user",)

    @admin.display(description="نام بیمار")
    def patient_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
