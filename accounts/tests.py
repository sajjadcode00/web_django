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

    def test_login_redirects_to_doctor_directory(self):
        self.client.post(reverse("accounts:register"), self.registration_data)

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "ali_test", "password": "Strong-Test-Password-2026"},
        )

        self.assertRedirects(response, reverse("accounts:doctor_list"))

    def test_failed_login_does_not_authenticate_user(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "unknown_user", "password": "Wrong-Test-Password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

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


class DoctorRegistrationAndSearchTests(TestCase):
    def setUp(self):
        self.clinic = Clinic.objects.create(
            name="کلینیک پزشکان",
            address="تبریز",
            phone_number="04112345678",
        )
        self.doctor_data = {
            "first_name": "مریم",
            "last_name": "کریمی",
            "username": "maryam_doctor",
            "specialty": "پوست و مو",
            "medical_system_number": "DOC-9001",
            "clinic": str(self.clinic.pk),
            "password1": "Strong-Test-Password-2026",
            "password2": "Strong-Test-Password-2026",
        }

    def test_doctor_registration_creates_inactive_user_and_doctor_profile(self):
        response = self.client.post(
            reverse("accounts:doctor_register"),
            self.doctor_data,
        )
        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(username="maryam_doctor")
        doctor = Doctor.objects.get(user=user)
        self.assertFalse(user.is_active)
        self.assertEqual(doctor.specialty, "پوست و مو")
        self.assertEqual(doctor.clinic, self.clinic)

    def test_doctor_registration_rejects_duplicate_medical_system_number(self):
        existing_user = User.objects.create_user(username="existing_doctor")
        Doctor.objects.create(
            user=existing_user,
            specialty="داخلی",
            medical_system_number="DOC-9001",
        )
        response = self.client.post(
            reverse("accounts:doctor_register"),
            self.doctor_data,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "این شماره نظام پزشکی قبلاً ثبت شده است.")
        self.assertFalse(User.objects.filter(username="maryam_doctor").exists())

    def test_active_doctor_login_redirects_to_doctor_dashboard(self):
        doctor_user = User.objects.create_user(
            username="active_doctor_login",
            password="Strong-Test-Password-2026",
            is_active=True,
        )
        Doctor.objects.create(
            user=doctor_user,
            specialty="داخلی",
            medical_system_number="DOC-9002",
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "active_doctor_login", "password": "Strong-Test-Password-2026"},
        )
        self.assertRedirects(response, reverse("bookings:doctor_dashboard"))

    def test_doctor_search_matches_name_and_specialty(self):
        doctor_user = User.objects.create_user(
            username="search_doctor",
            first_name="نیلوفر",
            last_name="احمدی",
        )
        doctor = Doctor.objects.create(
            user=doctor_user,
            specialty="قلب و عروق",
            medical_system_number="DOC-9003",
        )
        patient_user = User.objects.create_user(username="search_patient")
        Patient.objects.create(
            user=patient_user,
            national_id="1234567801",
            phone_number="09123456780",
        )
        self.client.force_login(patient_user)

        by_name = self.client.get(reverse("accounts:doctor_list"), {"q": "نیلوفر"})
        self.assertContains(by_name, "نیلوفر احمدی")
        by_full_name = self.client.get(reverse("accounts:doctor_list"), {"q": "نیلوفر احمدی"})
        self.assertContains(by_full_name, "نیلوفر احمدی")
        by_specialty = self.client.get(reverse("accounts:doctor_list"), {"specialty": "قلب و عروق"})
        self.assertContains(by_specialty, "نیلوفر احمدی")
        self.assertEqual(doctor.pk, Doctor.objects.get(user=doctor_user).pk)


class DoctorAdminApprovalTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="approval_admin",
            email="admin@example.test",
            password="Strong-Admin-Password-2026",
        )
        doctor_user = User.objects.create_user(
            username="pending_doctor",
            password="Strong-Doctor-Password-2026",
            first_name="پزشک",
            last_name="در انتظار",
            is_active=False,
        )
        self.doctor = Doctor.objects.create(
            user=doctor_user,
            specialty="داخلی",
            medical_system_number="PENDING-100",
        )

    def test_admin_can_activate_pending_doctor_from_doctor_changelist(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("admin:accounts_doctor_changelist"),
            {
                "action": "activate_doctor_accounts",
                "_selected_action": [str(self.doctor.pk)],
                "index": "0",
            },
            follow=True,
        )
        self.doctor.user.refresh_from_db()
        self.assertTrue(self.doctor.user.is_active)
        self.assertEqual(response.status_code, 200)
