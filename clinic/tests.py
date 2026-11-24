from django.test import TestCase

from .models import Clinic


class ClinicModelTests(TestCase):
    def test_clinic_has_readable_string_representation(self):
        clinic = Clinic.objects.create(
            name="کلینیک نمونه",
            address="تبریز",
            phone_number="04112345678",
        )

        self.assertEqual(str(clinic), "کلینیک نمونه")
