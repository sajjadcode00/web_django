from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Doctor, Patient
from clinic.models import Clinic

from .models import Appointment, AppointmentNotification, DoctorSchedule

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
        DoctorSchedule.objects.create(
            doctor=self.doctor,
            weekday=self.future_date.weekday(),
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_duration_minutes=30,
        )
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
        response = self.client.get(
            self.booking_url,
            {"date": self.future_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "درخواست رزرو نوبت")
        self.assertContains(response, "دکتر سارا احمدی")
        self.assertContains(response, 'type="date"')
        self.assertContains(response, '<select')
        self.assertContains(response, '10:30')

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
            reverse("bookings:doctor_dashboard"),
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


class DoctorScheduleAndPortalTests(TestCase):
    def setUp(self):
        self.clinic = Clinic.objects.create(
            name="کلینیک برنامه",
            address="تبریز",
            phone_number="04100000002",
        )
        self.doctor_user = User.objects.create_user(
            username="schedule_doctor",
            password="Strong-Test-Password-2026",
            first_name="رضا",
            last_name="محمدی",
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            clinic=self.clinic,
            specialty="داخلی",
            medical_system_number="SCH-100",
        )
        patient_user = User.objects.create_user(username="schedule_patient")
        self.patient = Patient.objects.create(
            user=patient_user,
            national_id="1234567802",
            phone_number="09123456781",
        )
        self.patient_user = patient_user
        self.future_date = timezone.localdate() + timedelta(days=5)

    def test_doctor_can_create_weekly_attendance_window(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("bookings:doctor_schedule"),
            {
                "weekday": self.future_date.weekday(),
                "start_time": "09:00",
                "end_time": "11:00",
                "slot_duration_minutes": 30,
            },
        )
        self.assertRedirects(response, reverse("bookings:doctor_schedule"))
        schedule = DoctorSchedule.objects.get(doctor=self.doctor)
        self.assertEqual(schedule.start_time, time(9, 0))
        self.assertEqual(schedule.end_time, time(11, 0))

    def test_doctor_cannot_create_overlapping_attendance_windows(self):
        DoctorSchedule.objects.create(
            doctor=self.doctor,
            weekday=self.future_date.weekday(),
            start_time=time(9, 0),
            end_time=time(11, 0),
        )
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("bookings:doctor_schedule"),
            {
                "weekday": self.future_date.weekday(),
                "start_time": "10:00",
                "end_time": "12:00",
                "slot_duration_minutes": 30,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هم‌پوشانی")
        self.assertEqual(DoctorSchedule.objects.filter(doctor=self.doctor).count(), 1)

    def test_patient_cannot_open_doctor_schedule_management(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("bookings:doctor_schedule"))
        self.assertEqual(response.status_code, 404)

    def test_doctor_can_view_patient_information_for_own_appointments(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
        )
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("bookings:doctor_appointments"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.national_id)
        self.assertContains(response, self.patient.phone_number)
        self.assertContains(response, "schedule_patient")
        self.assertContains(response, str(appointment.appointment_date.year))

    def test_patient_can_view_only_their_own_appointments(self):
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
        )
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("bookings:patient_appointments"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "دکتر رضا محمدی")

    def test_patient_can_cancel_their_own_appointment_and_free_the_slot(self):
        DoctorSchedule.objects.create(
            doctor=self.doctor,
            weekday=self.future_date.weekday(),
            start_time=time(9, 0),
            end_time=time(11, 0),
            slot_duration_minutes=30,
        )
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(9, 30),
        )
        self.client.force_login(self.patient_user)
        response = self.client.post(
            reverse("bookings:cancel_patient_appointment", args=[appointment.pk])
        )
        appointment.refresh_from_db()
        self.assertRedirects(response, reverse("bookings:patient_appointments"))
        self.assertEqual(appointment.status, "CANCELLED")

        from .services import available_slots_for
        self.assertIn(time(9, 30), available_slots_for(self.doctor, self.future_date))

    def test_patient_cannot_cancel_another_patients_appointment(self):
        other_user = User.objects.create_user(username="not_owner_patient")
        other_patient = Patient.objects.create(
            user=other_user,
            national_id="1234567803",
            phone_number="09123456782",
        )
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=other_patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
        )
        self.client.force_login(self.patient_user)
        response = self.client.post(
            reverse("bookings:cancel_patient_appointment", args=[appointment.pk])
        )
        self.assertEqual(response.status_code, 404)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "PENDING")

    def test_booking_page_shows_only_free_slots_from_doctor_schedule(self):
        DoctorSchedule.objects.create(
            doctor=self.doctor,
            weekday=self.future_date.weekday(),
            start_time=time(9, 0),
            end_time=time(10, 30),
            slot_duration_minutes=30,
        )
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(9, 30),
        )
        self.client.force_login(self.patient_user)
        response = self.client.get(
            reverse("bookings:create", args=[self.doctor.pk]),
            {"date": self.future_date.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "09:00")
        self.assertNotContains(response, '<option value="09:30">09:30</option>')
        self.assertContains(response, "10:00")

    def test_booking_rejects_a_time_outside_doctor_schedule(self):
        DoctorSchedule.objects.create(
            doctor=self.doctor,
            weekday=self.future_date.weekday(),
            start_time=time(9, 0),
            end_time=time(11, 0),
            slot_duration_minutes=30,
        )
        self.client.force_login(self.patient_user)
        response = self.client.post(
            reverse("bookings:create", args=[self.doctor.pk]),
            {
                "appointment_date": self.future_date.isoformat(),
                "appointment_time": "15:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "این ساعت در برنامه حضور پزشک وجود ندارد")
        self.assertEqual(Appointment.objects.count(), 0)

    def test_doctor_cannot_view_another_doctors_appointments(self):
        other_user = User.objects.create_user(username="other_portal_doctor")
        other_doctor = Doctor.objects.create(
            user=other_user,
            specialty="چشم",
            medical_system_number="SCH-101",
        )
        Appointment.objects.create(
            doctor=other_doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(9, 0),
        )
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("bookings:doctor_appointments"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "SCH-101")

    def test_patient_appointments_page_does_not_show_other_patients_records(self):
        other_user = User.objects.create_user(username="private_patient")
        other_patient = Patient.objects.create(
            user=other_user,
            national_id="1234567804",
            phone_number="09123456783",
        )
        Appointment.objects.create(
            doctor=self.doctor,
            patient=other_patient,
            appointment_date=self.future_date,
            appointment_time=time(9, 0),
        )
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("bookings:patient_appointments"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "private_patient")

    def test_doctor_can_confirm_their_own_pending_appointment(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse("bookings:confirm_doctor_appointment", args=[appointment.pk])
        )

        appointment.refresh_from_db()
        self.assertRedirects(response, reverse("bookings:doctor_appointments"))
        self.assertEqual(appointment.status, "CONFIRMED")
        notification = AppointmentNotification.objects.get(appointment=appointment)
        self.assertEqual(notification.recipient, self.patient_user)
        self.assertEqual(notification.event_type, "CONFIRMED")

    def test_doctor_can_reject_their_own_pending_appointment_and_free_slot(self):
        DoctorSchedule.objects.create(
            doctor=self.doctor,
            weekday=self.future_date.weekday(),
            start_time=time(9, 0),
            end_time=time(11, 0),
            slot_duration_minutes=30,
        )
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse("bookings:reject_doctor_appointment", args=[appointment.pk])
        )

        appointment.refresh_from_db()
        self.assertRedirects(response, reverse("bookings:doctor_appointments"))
        self.assertEqual(appointment.status, "REJECTED")
        notification = AppointmentNotification.objects.get(appointment=appointment)
        self.assertEqual(notification.recipient, self.patient_user)
        self.assertEqual(notification.event_type, "REJECTED")

        from .services import available_slots_for
        self.assertIn(time(10, 0), available_slots_for(self.doctor, self.future_date))

    def test_patient_cannot_confirm_an_appointment(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
        )
        self.client.force_login(self.patient_user)

        response = self.client.post(
            reverse("bookings:confirm_doctor_appointment", args=[appointment.pk])
        )

        appointment.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(appointment.status, "PENDING")

    def test_doctor_cannot_change_another_doctors_appointment(self):
        other_user = User.objects.create_user(username="another_action_doctor")
        other_doctor = Doctor.objects.create(
            user=other_user,
            specialty="چشم",
            medical_system_number="ACT-101",
        )
        appointment = Appointment.objects.create(
            doctor=other_doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse("bookings:confirm_doctor_appointment", args=[appointment.pk])
        )

        appointment.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(appointment.status, "PENDING")

    def test_doctor_appointments_page_shows_confirm_and_reject_actions_for_pending(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
        )
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse("bookings:doctor_appointments"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "تأیید نوبت")
        self.assertContains(response, "رد درخواست")
        self.assertContains(
            response,
            reverse("bookings:confirm_doctor_appointment", args=[appointment.pk]),
        )


    def test_patient_sees_unread_notification_badge_and_notification_list(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
            status="CONFIRMED",
        )
        notification = AppointmentNotification.objects.create(
            recipient=self.patient_user,
            appointment=appointment,
            event_type="CONFIRMED",
            message="درخواست نوبت شما تأیید شد.",
        )
        self.client.force_login(self.patient_user)

        response = self.client.get(reverse("bookings:notifications"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "اعلانات")
        self.assertContains(response, "درخواست نوبت شما تأیید شد.")
        self.assertContains(response, 'class="header-notification-count"')
        self.assertContains(response, reverse("bookings:open_notification", args=[notification.pk]))

    def test_opening_notification_marks_it_read_and_shows_current_appointment_status(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
            status="CONFIRMED",
        )
        notification = AppointmentNotification.objects.create(
            recipient=self.patient_user,
            appointment=appointment,
            event_type="CONFIRMED",
            message="درخواست نوبت شما تأیید شد.",
        )
        self.client.force_login(self.patient_user)

        response = self.client.post(
            reverse("bookings:open_notification", args=[notification.pk])
        )

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertRedirects(response, reverse("bookings:success", args=[appointment.pk]))
        detail_response = self.client.get(response.url)
        self.assertContains(detail_response, "نوبت شما تأیید شده است")
        self.assertContains(detail_response, "تأیید شده")

    def test_patient_cannot_open_another_users_notification(self):
        other_user = User.objects.create_user(username="notification_other_patient")
        other_patient = Patient.objects.create(
            user=other_user,
            national_id="1234567810",
            phone_number="09123456790",
        )
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=other_patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
            status="REJECTED",
        )
        notification = AppointmentNotification.objects.create(
            recipient=other_user,
            appointment=appointment,
            event_type="REJECTED",
            message="درخواست نوبت رد شد.",
        )
        self.client.force_login(self.patient_user)

        response = self.client.post(
            reverse("bookings:open_notification", args=[notification.pk])
        )

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_doctor_is_not_shown_patient_notification_link(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("bookings:doctor_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("bookings:notifications"))

    def test_patient_cannot_cancel_an_appointment_rejected_by_doctor(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=self.future_date,
            appointment_time=time(10, 0),
            status="REJECTED",
        )
        self.client.force_login(self.patient_user)

        response = self.client.post(
            reverse("bookings:cancel_patient_appointment", args=[appointment.pk])
        )

        appointment.refresh_from_db()
        self.assertRedirects(response, reverse("bookings:patient_appointments"))
        self.assertEqual(appointment.status, "REJECTED")
