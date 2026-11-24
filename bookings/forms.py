from datetime import date, time

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Appointment, DoctorSchedule
from .services import available_slots_for


class AppointmentBookingForm(forms.ModelForm):
    """Collect a date and one currently available slot for a selected doctor."""

    appointment_time = forms.TimeField(
        input_formats=["%H:%M", "%H:%M:%S"],
        widget=forms.Select(attrs={"class": "booking-input"}),
        label="ساعت آزاد",
    )

    class Meta:
        model = Appointment
        fields = ("appointment_date", "appointment_time")
        widgets = {
            "appointment_date": forms.HiddenInput(),
        }
        labels = {"appointment_date": "تاریخ مراجعه"}

    def __init__(self, *args, doctor=None, selected_date=None, **kwargs):
        self.doctor = doctor
        super().__init__(*args, **kwargs)

        raw_date = None
        if self.is_bound:
            raw_date = self.data.get(self.add_prefix("appointment_date"))
        elif selected_date:
            raw_date = selected_date.isoformat() if hasattr(selected_date, "isoformat") else str(selected_date)
        else:
            raw_date = timezone.localdate().isoformat()

        try:
            self.selected_date = date.fromisoformat(raw_date)
        except (TypeError, ValueError):
            self.selected_date = timezone.localdate()

        self.available_slots = available_slots_for(self.doctor, self.selected_date) if self.doctor else []
        choices = [(slot.strftime("%H:%M"), slot.strftime("%H:%M")) for slot in self.available_slots]
        self.fields["appointment_time"].widget.choices = [("", "یک ساعت را انتخاب کنید")] + choices
        self.fields["appointment_time"].help_text = (
            "فقط ساعت‌هایی نمایش داده می‌شوند که پزشک برای این روز تعریف کرده و هنوز رزرو نشده‌اند."
        )
        self.fields["appointment_date"].initial = self.selected_date

    def clean_appointment_date(self):
        appointment_date = self.cleaned_data["appointment_date"]
        if appointment_date < timezone.localdate():
            raise ValidationError("امکان ثبت نوبت برای تاریخ‌های گذشته وجود ندارد.")
        return appointment_date

    def clean(self):
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get("appointment_date")
        appointment_time = cleaned_data.get("appointment_time")

        if not appointment_date or not appointment_time:
            return cleaned_data

        today = timezone.localdate()
        now = timezone.localtime().time().replace(second=0, microsecond=0)
        if appointment_date == today and appointment_time <= now:
            self.add_error("appointment_time", "برای امروز باید ساعتی در آینده انتخاب کنید.")
            return cleaned_data

        occupied = Appointment.objects.filter(
            doctor=self.doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
        ).exclude(status="CANCELLED")
        if occupied.exists():
            self.add_error(
                "appointment_time",
                "این زمان برای پزشک انتخاب‌شده قبلاً رزرو شده است. لطفاً ساعت دیگری انتخاب کنید.",
            )
        elif appointment_time not in available_slots_for(self.doctor, appointment_date):
            self.add_error(
                "appointment_time",
                "این ساعت در برنامه حضور پزشک وجود ندارد یا دیگر آزاد نیست.",
            )

        return cleaned_data


class DoctorScheduleForm(forms.ModelForm):
    class Meta:
        model = DoctorSchedule
        fields = ("weekday", "start_time", "end_time", "slot_duration_minutes")
        widgets = {
            "weekday": forms.Select(attrs={"class": "workflow-input"}),
            "start_time": forms.TimeInput(attrs={"class": "workflow-input", "type": "time"}),
            "end_time": forms.TimeInput(attrs={"class": "workflow-input", "type": "time"}),
            "slot_duration_minutes": forms.Select(attrs={"class": "workflow-input"}),
        }
        labels = {
            "weekday": "روز هفته",
            "start_time": "ساعت شروع حضور",
            "end_time": "ساعت پایان حضور",
            "slot_duration_minutes": "مدت هر نوبت",
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if start_time and end_time and start_time >= end_time:
            self.add_error("end_time", "ساعت پایان باید بعد از ساعت شروع باشد.")
        return cleaned_data
