from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.UniqueConstraint(
                fields=("doctor", "appointment_date", "appointment_time"),
                condition=Q(status__in=("PENDING", "CONFIRMED")),
                name="unique_active_doctor_appointment_slot",
            ),
        ),
    ]
