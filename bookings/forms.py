from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Appointment


class AppointmentBookingForm(forms.ModelForm):
    """Collect a requested date and time for one doctor."""

    class Meta:
        model = Appointment
        fields = ("appointment_date", "appointment_time")
        widgets = {
            "appointment_date": forms.DateInput(
                attrs={
                    "class": "booking-input",
                    "type": "date",
                    "autocomplete": "off",
                }
            ),
            "appointment_time": forms.TimeInput(
                attrs={
                    "class": "booking-input",
                    "type": "time",
                    "autocomplete": "off",
                }
            ),
        }
        labels = {
            "appointment_date": "تاریخ موردنظر",
            "appointment_time": "ساعت موردنظر",
        }

    def __init__(self, *args, doctor=None, **kwargs):
        self.doctor = doctor
        super().__init__(*args, **kwargs)
        self.fields["appointment_date"].help_text = "تاریخ‌های گذشته قابل انتخاب نیستند."
        self.fields["appointment_time"].help_text = "ساعت را بر اساس زمان محلی کلینیک انتخاب کنید."
        self.fields["appointment_date"].widget.attrs["min"] = timezone.localdate().isoformat()

    def clean_appointment_date(self):
        appointment_date = self.cleaned_data["appointment_date"]
        if appointment_date < timezone.localdate():
            raise ValidationError("امکان ثبت نوبت برای تاریخ‌های گذشته وجود ندارد.")
        return appointment_date

    def clean(self):
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get("appointment_date")
        appointment_time = cleaned_data.get("appointment_time")

        if appointment_date and appointment_time:
            today = timezone.localdate()
            current_time = timezone.localtime().time().replace(second=0, microsecond=0)
            if appointment_date == today and appointment_time <= current_time:
                self.add_error(
                    "appointment_time",
                    "برای امروز باید ساعتی در آینده انتخاب کنید.",
                )

        if self.doctor and appointment_date and appointment_time:
            occupied_slot = Appointment.objects.filter(
                doctor=self.doctor,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
            ).exclude(status="CANCELLED")

            if self.instance.pk:
                occupied_slot = occupied_slot.exclude(pk=self.instance.pk)

            if occupied_slot.exists():
                self.add_error(
                    "appointment_time",
                    "این زمان برای پزشک انتخاب‌شده قبلاً رزرو شده است. لطفاً ساعت دیگری انتخاب کنید.",
                )

        return cleaned_data
