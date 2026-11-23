from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Doctor, Patient
from clinic.models import Clinic

User = get_user_model()


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.registration_data = {
            "first_name": "علی",
            "last_name": "رضایی",
            "username": "ali_test",
            "national_id": "1234567890",
            "phone_number": "09123456789",
            "password1": "Strong-Test-Password-2026",
            "password2": "Strong-Test-Password-2026",
        }

    def test_home_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_registration_creates_user_and_patient_then_redirects_to_login(self):
        response = self.client.post(reverse("accounts:register"), self.registration_data)

        self.assertRedirects(response, reverse("accounts:login"))
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Patient.objects.count(), 1)

        user = User.objects.get(username="ali_test")
        self.assertTrue(user.check_password("Strong-Test-Password-2026"))
        self.assertEqual(user.first_name, "علی")
        self.assertEqual(user.patient.national_id, "1234567890")
        self.assertEqual(user.patient.phone_number, "09123456789")

    def test_registration_accepts_persian_digits_for_national_id_and_phone(self):
        data = self.registration_data.copy()
        data["username"] = "persian_digits"
        data["national_id"] = "۱۲۳۴۵۶۷۸۹۱"
        data["phone_number"] = "۰۹۱۲۳۴۵۶۷۸۹"

        response = self.client.post(reverse("accounts:register"), data)

        self.assertRedirects(response, reverse("accounts:login"))
        patient = Patient.objects.get(user__username="persian_digits")
        self.assertEqual(patient.national_id, "1234567891")
        self.assertEqual(patient.phone_number, "09123456789")

    def test_registration_rejects_duplicate_national_id(self):
        response = self.client.post(reverse("accounts:register"), self.registration_data)
        self.assertRedirects(response, reverse("accounts:login"))

        second_data = self.registration_data.copy()
        second_data["username"] = "another_user"
        response = self.client.post(reverse("accounts:register"), second_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "با این کد ملی قبلاً حساب کاربری ساخته شده است.")
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Patient.objects.count(), 1)

    def test_login_redirects_to_dashboard(self):
        self.client.post(reverse("accounts:register"), self.registration_data)

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "ali_test", "password": "Strong-Test-Password-2026"},
        )

        self.assertRedirects(response, reverse("accounts:doctor_list"))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        expected = f"{reverse('accounts:login')}?next={reverse('accounts:dashboard')}"
        self.assertRedirects(response, expected)

    def test_logout_uses_post_and_returns_to_login(self):
        user = User.objects.create_user(username="logout_test", password="Strong-Test-Password-2026")
        self.client.force_login(user)

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("accounts:login"))
        dashboard_response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(dashboard_response.status_code, 302)


class DoctorDirectoryTests(TestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            username="patient_viewer",
            password="Strong-Test-Password-2026",
        )
        self.client.force_login(self.patient_user)

        self.clinic = Clinic.objects.create(
            name="کلینیک نمونه",
            address="تبریز، خیابان نمونه",
            phone_number="04100000000",
        )

    def create_doctor(self, username, first_name, last_name, specialty, active=True):
        user = User.objects.create_user(
            username=username,
            password="Strong-Test-Password-2026",
            first_name=first_name,
            last_name=last_name,
            is_active=active,
        )
        return Doctor.objects.create(
            user=user,
            clinic=self.clinic,
            specialty=specialty,
            medical_system_number=f"TEST-{username}",
        )

    def test_doctor_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("accounts:doctor_list"))

        expected = f"{reverse('accounts:login')}?next={reverse('accounts:doctor_list')}"
        self.assertRedirects(response, expected)

    def test_doctor_list_shows_doctor_name_specialty_and_clinic(self):
        self.create_doctor(
            "doctor_sara", "سارا", "احمدی", "قلب و عروق"
        )

        response = self.client.get(reverse("accounts:doctor_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "دکتر سارا احمدی")
        self.assertContains(response, "قلب و عروق")
        self.assertContains(response, "کلینیک نمونه")
        self.assertEqual(response.context["doctor_count"], 1)

    def test_doctor_list_does_not_show_inactive_doctors(self):
        self.create_doctor(
            "doctor_inactive", "پزشک", "غیرفعال", "داخلی", active=False
        )

        response = self.client.get(reverse("accounts:doctor_list"))

        self.assertNotContains(response, "پزشک غیرفعال")
        self.assertEqual(response.context["doctor_count"], 0)

    def test_dashboard_redirects_to_doctor_list(self):
        response = self.client.get(reverse("accounts:dashboard"))

        self.assertRedirects(response, reverse("accounts:doctor_list"))


class DoctorDetailTests(TestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            username="profile_viewer",
            password="Strong-Test-Password-2026",
        )
        self.clinic = Clinic.objects.create(
            name="کلینیک مهر",
            address="تبریز، خیابان آزادی، پلاک ۱۰",
            phone_number="04112345678",
        )
        doctor_user = User.objects.create_user(
            username="doctor_profile",
            password="Strong-Test-Password-2026",
            first_name="سارا",
            last_name="احمدی",
        )
        self.doctor = Doctor.objects.create(
            user=doctor_user,
            clinic=self.clinic,
            specialty="قلب و عروق",
            medical_system_number="123456",
        )

    def test_doctor_detail_requires_login(self):
        response = self.client.get(
            reverse("accounts:doctor_detail", args=[self.doctor.id])
        )
        expected = (
            f"{reverse('accounts:login')}?next="
            f"{reverse('accounts:doctor_detail', args=[self.doctor.id])}"
        )
        self.assertRedirects(response, expected)

    def test_doctor_detail_shows_doctor_and_clinic_information(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(
            reverse("accounts:doctor_detail", args=[self.doctor.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "دکتر سارا احمدی")
        self.assertContains(response, "قلب و عروق")
        self.assertContains(response, "123456")
        self.assertContains(response, "کلینیک مهر")
        self.assertContains(response, "تبریز، خیابان آزادی، پلاک ۱۰")
        self.assertContains(response, "04112345678")

    def test_doctor_list_links_to_doctor_detail(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("accounts:doctor_list"))

        self.assertContains(
            response,
            reverse("accounts:doctor_detail", args=[self.doctor.id]),
        )

    def test_unknown_doctor_returns_404(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(
            reverse("accounts:doctor_detail", args=[99999])
        )
        self.assertEqual(response.status_code, 404)

    def test_inactive_doctor_profile_returns_404(self):
        self.doctor.user.is_active = False
        self.doctor.user.save(update_fields=["is_active"])
        self.client.force_login(self.patient_user)

        response = self.client.get(
            reverse("accounts:doctor_detail", args=[self.doctor.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_doctor_without_clinic_has_fallback_message(self):
        self.doctor.clinic = None
        self.doctor.save(update_fields=["clinic"])
        self.client.force_login(self.patient_user)

        response = self.client.get(
            reverse("accounts:doctor_detail", args=[self.doctor.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "اطلاعات کلینیک برای این پزشک هنوز ثبت نشده است.")
