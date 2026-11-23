from django.db import models
from django.contrib.auth.models import User
from clinic.models import Clinic



class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.SET_NULL, null=True, related_name='doctors')
    specialty = models.CharField(max_length=100)
    medical_system_number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        full_name = self.user.get_full_name().strip() or self.user.username
        return f"دکتر {full_name} - {self.specialty}"

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    national_id = models.CharField(max_length=10, unique=True)
    phone_number = models.CharField(max_length=11)

    def __str__(self):
        return self.user.get_full_name().strip() or self.user.username
