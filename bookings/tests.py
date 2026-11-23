from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Doctor, Patient
from clinic.models import Clinic

from .models import Appointment

User = get_user_model()


class AppointmentBookingTests(TestCase):
    def setUp(self):
        self.clinic = Clinic.objects.create(
            name="کلینیک سلامت",
            address="تبریز، خیابان آزادی",
            phone_number="04112345678",
        )
        doctor_user = User.objects.create_user(
            username="doctor_one",
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

        patient_user = User.objects.create_user(
            username="patient_one",
            password="Strong-Test-Password-2026",
            first_name="علی",
            last_name="رضایی",
        )
        self.patient = Patient.objects.create(
            user=patient_user,
            national_id="1234567890",
            phone_number="09123456789",
        )
        self.patient_user = patient_user
        self.booking_url = reverse("bookings:create", args=[self.doctor.pk])
        self.future_date = timezone.localdate() + timedelta(days=3)
        self.valid_data = {
            "appointment_date": self.future_date.isoformat(),
            "appointment_time": "10:30",
        }

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.booking_url)
        expected = f"{reverse('accounts:login')}?next={self.booking_url}"
        self.assertRedirects(response, expected)

    def test_patient_can_open_booking_form(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(self.booking_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "درخواست رزرو نوبت")
        self.assertContains(response, "دکتر سارا احمدی")
        self.assertContains(response, 'type="date"')
        self.assertContains(response, 'type="time"')

    def test_valid_booking_is_created_for_logged_in_patient_and_doctor(self):
        self.client.force_login(self.patient_user)
        response = self.client.post(self.booking_url, self.valid_data)

        appointment = Appointment.objects.get()
        self.assertRedirects(
            response,
            reverse("bookings:success", args=[appointment.pk]),
        )
        self.assertEqual(appointment.doctor, self.doctor)
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.status, "PENDING")

    def test_success_page_shows_booking_details_to_owner(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 30),
        )
        self.client.force_login(self.patient_user)

        response = self.client.get(
            reverse("bookings:success", args=[appointment.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "در انتظار تأیید")
        self.assertContains(response, "کد پیگیری")
        self.assertContains(response, str(appointment.pk))

    def test_other_patient_cannot_view_booking_success_page(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 30),
        )
        other_user = User.objects.create_user(
            username="patient_two",
            password="Strong-Test-Password-2026",
        )
        Patient.objects.create(
            user=other_user,
            national_id="1234567891",
            phone_number="09123456780",
        )
        self.client.force_login(other_user)

        response = self.client.get(
            reverse("bookings:success", args=[appointment.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_past_date_is_rejected(self):
        self.client.force_login(self.patient_user)
        data = self.valid_data.copy()
        data["appointment_date"] = (timezone.localdate() - timedelta(days=1)).isoformat()

        response = self.client.post(self.booking_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "امکان ثبت نوبت برای تاریخ‌های گذشته وجود ندارد.")
        self.assertEqual(Appointment.objects.count(), 0)

    def test_past_time_today_is_rejected(self):
        self.client.force_login(self.patient_user)
        data = {
            "appointment_date": timezone.localdate().isoformat(),
            "appointment_time": "00:00",
        }

        response = self.client.post(self.booking_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "برای امروز باید ساعتی در آینده انتخاب کنید.")
        self.assertEqual(Appointment.objects.count(), 0)

    def test_same_doctor_date_and_time_cannot_be_booked_twice(self):
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 30),
        )
        self.client.force_login(self.patient_user)

        response = self.client.post(self.booking_url, self.valid_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "این زمان برای پزشک انتخاب‌شده قبلاً رزرو شده است.")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_cancelled_appointment_does_not_block_slot(self):
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 30),
            status="CANCELLED",
        )
        self.client.force_login(self.patient_user)

        response = self.client.post(self.booking_url, self.valid_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Appointment.objects.count(), 2)
        self.assertEqual(
            Appointment.objects.filter(status="PENDING").count(),
            1,
        )

    def test_user_without_patient_profile_cannot_book(self):
        doctor_user = self.doctor.user
        self.client.force_login(doctor_user)

        response = self.client.post(self.booking_url, self.valid_data)

        self.assertRedirects(
            response,
            reverse("accounts:doctor_detail", args=[self.doctor.pk]),
        )
        self.assertEqual(Appointment.objects.count(), 0)

    def test_inactive_doctor_cannot_be_booked(self):
        self.doctor.user.is_active = False
        self.doctor.user.save(update_fields=["is_active"])
        self.client.force_login(self.patient_user)

        response = self.client.get(self.booking_url)

        self.assertEqual(response.status_code, 404)

    def test_database_constraint_rejects_duplicate_active_slot(self):
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 30),
        )
        second_user = User.objects.create_user(
            username="patient_three",
            password="Strong-Test-Password-2026",
        )
        second_patient = Patient.objects.create(
            user=second_user,
            national_id="1234567892",
            phone_number="09123456781",
        )

        with self.assertRaises(IntegrityError):
            Appointment.objects.create(
                doctor=self.doctor,
                patient=second_patient,
                appointment_date=self.future_date,
                appointment_time=time(10, 30),
            )


class AppointmentModelStringTests(TestCase):
    def test_appointment_has_readable_string_representation(self):
        clinic = Clinic.objects.create(
            name="کلینیک نمونه",
            address="نشانی نمونه",
            phone_number="04112345678",
        )
        doctor_user = User.objects.create_user(
            username="doctor_string",
            first_name="مریم",
            last_name="کریمی",
        )
        doctor = Doctor.objects.create(
            user=doctor_user,
            clinic=clinic,
            specialty="پوست",
            medical_system_number="654321",
        )
        patient_user = User.objects.create_user(
            username="patient_string",
            first_name="رضا",
            last_name="محمدی",
        )
        patient = Patient.objects.create(
            user=patient_user,
            national_id="1234567893",
            phone_number="09123456782",
        )
        appointment = Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            appointment_date=timezone.localdate() + timedelta(days=2),
            appointment_time=time(9, 0),
        )

        self.assertIn("رضا محمدی", str(appointment))
        self.assertIn("مریم کریمی", str(appointment))
