from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0003_alter_appointment_options_alter_appointment_status_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="appointment",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "در انتظار تأیید"),
                    ("CONFIRMED", "تأیید شده"),
                    ("REJECTED", "رد شده توسط پزشک"),
                    ("CANCELLED", "لغو شده توسط بیمار"),
                ],
                default="PENDING",
                max_length=10,
            ),
        ),
    ]
