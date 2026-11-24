from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.db.models import F, Q

from accounts.models import Doctor, Patient


class DoctorSchedule(models.Model):
    """A recurring weekly attendance window for one doctor."""

    WEEKDAYS = [
        (0, "دوشنبه"),
        (1, "سه‌شنبه"),
        (2, "چهارشنبه"),
        (3, "پنجشنبه"),
        (4, "جمعه"),
        (5, "شنبه"),
        (6, "یکشنبه"),
    ]
    SLOT_DURATIONS = [
        (15, "۱۵ دقیقه"),
        (20, "۲۰ دقیقه"),
        (30, "۳۰ دقیقه"),
        (45, "۴۵ دقیقه"),
        (60, "۶۰ دقیقه"),
    ]

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.PositiveSmallIntegerField(
        choices=SLOT_DURATIONS,
        default=30,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("weekday", "start_time")
        constraints = [
            models.UniqueConstraint(
                fields=("doctor", "weekday", "start_time", "end_time"),
                name="unique_doctor_weekday_schedule_window",
            ),
            models.CheckConstraint(
                condition=Q(start_time__lt=F("end_time")),
                name="doctor_schedule_start_before_end",
            ),
        ]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({"end_time": "ساعت پایان باید بعد از ساعت شروع باشد."})

        if self.doctor_id and self.weekday is not None and self.start_time and self.end_time:
            overlapping = DoctorSchedule.objects.filter(
                doctor_id=self.doctor_id,
                weekday=self.weekday,
                is_active=True,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError("این بازه زمانی با یکی از برنامه‌های حضور قبلی هم‌پوشانی دارد.")

    def __str__(self):
        weekday_label = self.get_weekday_display()
        return f"{self.doctor} | {weekday_label} | {self.start_time:%H:%M}-{self.end_time:%H:%M}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "در انتظار تأیید"),
        ("CONFIRMED", "تأیید شده"),
        ("REJECTED", "رد شده توسط پزشک"),
        ("CANCELLED", "لغو شده توسط بیمار"),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="appointments")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("appointment_date", "appointment_time")
        constraints = [
            models.UniqueConstraint(
                fields=("doctor", "appointment_date", "appointment_time"),
                condition=Q(status__in=("PENDING", "CONFIRMED")),
                name="unique_active_doctor_appointment_slot",
            )
        ]

    def __str__(self):
        patient_name = self.patient.user.get_full_name().strip() or self.patient.user.username
        doctor_name = self.doctor.user.get_full_name().strip() or self.doctor.user.username
        return f"نوبت {patient_name} با دکتر {doctor_name} در {self.appointment_date}"


class AppointmentNotification(models.Model):
    """An in-site notification sent to a patient after a doctor reviews a booking."""

    EVENT_CHOICES = [
        ("CONFIRMED", "تأیید نوبت"),
        ("REJECTED", "رد درخواست"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointment_notifications",
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event_type = models.CharField(max_length=12, choices=EVENT_CHOICES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("appointment", "event_type"),
                name="unique_appointment_status_notification",
            )
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.recipient}"
