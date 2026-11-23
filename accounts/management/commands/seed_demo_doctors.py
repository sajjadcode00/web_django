from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Doctor
from clinic.models import Clinic


class Command(BaseCommand):
    help = "Create a small set of clearly marked demo clinics and doctors."

    DEMO_DATA = [
        {
            "username": "demo_dr_sara",
            "first_name": "سارا",
            "last_name": "احمدی",
            "specialty": "قلب و عروق",
            "medical_system_number": "DEMO-1001",
            "clinic": "کلینیک سلامت نو",
            "address": "تبریز، خیابان آزادی (نشانی نمونه)",
            "phone_number": "04100000001",
        },
        {
            "username": "demo_dr_reza",
            "first_name": "رضا",
            "last_name": "محمدی",
            "specialty": "مغز و اعصاب",
            "medical_system_number": "DEMO-1002",
            "clinic": "مرکز پزشکی سپید",
            "address": "تبریز، ولیعصر (نشانی نمونه)",
            "phone_number": "04100000002",
        },
        {
            "username": "demo_dr_niloofar",
            "first_name": "نیلوفر",
            "last_name": "کریمی",
            "specialty": "پوست و مو",
            "medical_system_number": "DEMO-1003",
            "clinic": "کلینیک سلامت نو",
            "address": "تبریز، خیابان آزادی (نشانی نمونه)",
            "phone_number": "04100000001",
        },
        {
            "username": "demo_dr_amir",
            "first_name": "امیر",
            "last_name": "حسینی",
            "specialty": "ارتوپدی",
            "medical_system_number": "DEMO-1004",
            "clinic": "درمانگاه مهر",
            "address": "تبریز، منظریه (نشانی نمونه)",
            "phone_number": "04100000003",
        },
        {
            "username": "demo_dr_mina",
            "first_name": "مینا",
            "last_name": "جعفری",
            "specialty": "زنان و زایمان",
            "medical_system_number": "DEMO-1005",
            "clinic": "مرکز پزشکی سپید",
            "address": "تبریز، ولیعصر (نشانی نمونه)",
            "phone_number": "04100000002",
        },
        {
            "username": "demo_dr_pouya",
            "first_name": "پویا",
            "last_name": "رحیمی",
            "specialty": "داخلی",
            "medical_system_number": "DEMO-1006",
            "clinic": "درمانگاه مهر",
            "address": "تبریز، منظریه (نشانی نمونه)",
            "phone_number": "04100000003",
        },
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        created_doctors = 0
        existing_doctors = 0

        for item in self.DEMO_DATA:
            clinic, _ = Clinic.objects.get_or_create(
                name=item["clinic"],
                defaults={
                    "address": item["address"],
                    "phone_number": item["phone_number"],
                },
            )

            user, user_created = User.objects.get_or_create(
                username=item["username"],
                defaults={
                    "first_name": item["first_name"],
                    "last_name": item["last_name"],
                    "is_active": True,
                },
            )

            if user_created:
                # Demo doctors do not need a usable login password.
                user.set_unusable_password()
                user.save(update_fields=["password"])

            _, doctor_created = Doctor.objects.get_or_create(
                user=user,
                defaults={
                    "clinic": clinic,
                    "specialty": item["specialty"],
                    "medical_system_number": item["medical_system_number"],
                },
            )

            if doctor_created:
                created_doctors += 1
            else:
                existing_doctors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready. New doctors: {created_doctors}; already existed: {existing_doctors}."
            )
        )
        self.stdout.write(
            "These are sample records only. Replace or delete them before using real clinic data."
        )
