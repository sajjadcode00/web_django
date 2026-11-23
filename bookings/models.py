from django.db import models
from django.db.models import Q

from accounts.models import Doctor, Patient


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("CONFIRMED", "Confirmed"),
        ("CANCELLED", "Cancelled"),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="appointments")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
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
        return f"{patient_name} با دکتر {doctor_name} در {self.appointment_date} - {self.appointment_time}"
