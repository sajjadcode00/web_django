from django.db import models
from django.contrib.auth.models import User
from clinic.models import Clinic



class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.SET_NULL, null=True, related_name='doctors')
    specialty = models.CharField(max_length=100)
    medical_system_number = models.CharField(max_length=20, unique=True)

    def str(self):
        return f"Dr. {self.user.first_name} {self.user.last_name} - {self.specialty}"

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    national_id = models.CharField(max_length=10, unique=True)
    phone_number = models.CharField(max_length=11)

    def str(self):
        return f"{self.user.first_name} {self.user.last_name}"
