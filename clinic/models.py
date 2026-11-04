from django.db import models


class Clinic(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone_number = models.CharField(max_length=11)

    def __str__(self):
        return self.name