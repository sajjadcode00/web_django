from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Doctor, Patient

from .forms import AppointmentBookingForm, DoctorScheduleForm
from .models import Appointment, AppointmentNotification, DoctorSchedule


def _doctor_for_user(user):
    return get_object_or_404(
        Doctor.objects.filter(user__is_active=True).select_related("user", "clinic"),
        user=user,
    )


def _patient_for_user(user):
    return get_object_or_404(
        Patient.objects.select_related("user"),
        user=user,
    )


def _appointments_for_patient(patient):
    return Appointment.objects.filter(patient=patient).select_related(
        "doctor__user", "doctor__clinic", "patient__user"
    )


def _appointments_for_doctor(doctor):
    return Appointment.objects.filter(doctor=doctor).select_related(
        "doctor__user", "doctor__clinic", "patient__user"
    )


@login_required
def create_appointment(request, doctor_id):
    """Let an authenticated patient request one of a doctor's published free slots."""
    doctor = get_object_or_404(
        Doctor.objects.filter(user__is_active=True).select_related("user", "clinic"),
        pk=doctor_id,
    )

    patient = Patient.objects.filter(user=request.user).select_related("user").first()
    if patient is None:
        messages.error(request, "رزرو نوبت فقط با حساب کاربری بیمار امکان‌پذیر است.")
        if Doctor.objects.filter(user=request.user).exists():
            return redirect("bookings:doctor_dashboard")
        return redirect("accounts:doctor_detail", doctor_id=doctor.pk)

    if request.method == "POST":
        form = AppointmentBookingForm(request.POST, doctor=doctor)
        if form.is_valid():
            try:
                with transaction.atomic():
                    appointment = form.save(commit=False)
                    appointment.doctor = doctor
                    appointment.patient = patient
                    appointment.status = "PENDING"
                    appointment.save()
            except IntegrityError:
                form.add_error(
                    "appointment_time",
                    "این زمان همین الان توسط شخص دیگری رزرو شد. لطفاً زمان دیگری انتخاب کنید.",
                )
            else:
                messages.success(request, "درخواست نوبت شما با موفقیت ثبت شد.")
                return redirect("bookings:success", appointment_id=appointment.pk)
    else:
        form = AppointmentBookingForm(
            doctor=doctor,
            selected_date=request.GET.get("date"),
        )

    return render(
        request,
        "bookings/appointment_form.html",
        {
            "form": form,
            "doctor": doctor,
            "selected_date": form.selected_date,
            "available_slots": form.available_slots,
            "today": timezone.localdate(),
        },
    )


@login_required
def appointment_success(request, appointment_id):
    """Show a booking confirmation only to the patient who owns the appointment."""
    patient = _patient_for_user(request.user)
    appointment = get_object_or_404(
        _appointments_for_patient(patient),
        pk=appointment_id,
    )
    return render(
        request,
        "bookings/appointment_success.html",
        {"appointment": appointment},
    )


@login_required
def patient_appointments(request):
    """Show only the appointment history belonging to the logged-in patient."""
    patient = _patient_for_user(request.user)
    appointments = _appointments_for_patient(patient).order_by(
        "-appointment_date", "-appointment_time"
    )
    return render(
        request,
        "bookings/patient_appointments.html",
        {"appointments": appointments, "today": timezone.localdate()},
    )


@login_required
@require_POST
def cancel_patient_appointment(request, appointment_id):
    """Allow a patient to cancel only their own future appointment."""
    patient = _patient_for_user(request.user)
    appointment = get_object_or_404(
        _appointments_for_patient(patient),
        pk=appointment_id,
    )

    if appointment.status == "CANCELLED":
        messages.info(request, "این نوبت قبلاً لغو شده است.")
    elif appointment.status == "REJECTED":
        messages.info(request, "این درخواست قبلاً توسط پزشک رد شده است.")
    else:
        appointment_datetime = timezone.make_aware(
            datetime.combine(appointment.appointment_date, appointment.appointment_time),
            timezone.get_current_timezone(),
        )
        if appointment_datetime <= timezone.localtime():
            messages.error(request, "امکان لغو نوبت‌هایی که زمان آن‌ها گذشته است وجود ندارد.")
            return redirect("bookings:patient_appointments")
        appointment.status = "CANCELLED"
        appointment.save(update_fields=["status"])
        messages.success(request, "نوبت با موفقیت لغو شد و زمان آن دوباره آزاد است.")

    return redirect("bookings:patient_appointments")


@login_required
def doctor_dashboard(request):
    """Doctor-only landing page with schedule and appointment summaries."""
    doctor = _doctor_for_user(request.user)
    doctor_appointments = _appointments_for_doctor(doctor)
    upcoming = doctor_appointments.exclude(status__in=("CANCELLED", "REJECTED")).filter(
        appointment_date__gte=timezone.localdate()
    ).order_by("appointment_date", "appointment_time")[:5]
    return render(
        request,
        "bookings/doctor_dashboard.html",
        {
            "doctor": doctor,
            "schedule_count": DoctorSchedule.objects.filter(doctor=doctor, is_active=True).count(),
            "pending_count": doctor_appointments.filter(status="PENDING").count(),
            "upcoming_appointments": upcoming,
        },
    )


@login_required
def doctor_schedule(request):
    """Let a doctor create and review their own weekly attendance windows."""
    doctor = _doctor_for_user(request.user)
    if request.method == "POST":
        form = DoctorScheduleForm(request.POST)
        form.instance.doctor = doctor
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.doctor = doctor
            schedule.save()
            messages.success(request, "برنامه حضور با موفقیت ثبت شد.")
            return redirect("bookings:doctor_schedule")
    else:
        form = DoctorScheduleForm()

    schedules = DoctorSchedule.objects.filter(doctor=doctor).order_by("weekday", "start_time")
    return render(
        request,
        "bookings/doctor_schedule.html",
        {"doctor": doctor, "form": form, "schedules": schedules},
    )


@login_required
@require_POST
def delete_doctor_schedule(request, schedule_id):
    """Delete a schedule only when it belongs to the logged-in doctor."""
    doctor = _doctor_for_user(request.user)
    schedule = get_object_or_404(DoctorSchedule, pk=schedule_id, doctor=doctor)
    schedule.delete()
    messages.success(request, "بازه حضور حذف شد.")
    return redirect("bookings:doctor_schedule")


@login_required
def doctor_appointments(request):
    """Show appointments and contact details for patients booked with this doctor."""
    doctor = _doctor_for_user(request.user)
    appointments = _appointments_for_doctor(doctor).order_by(
        "appointment_date", "appointment_time"
    )
    return render(
        request,
        "bookings/doctor_appointments.html",
        {"doctor": doctor, "appointments": appointments},
    )


@login_required
@require_POST
@transaction.atomic
def confirm_doctor_appointment(request, appointment_id):
    """Confirm a pending appointment belonging to the logged-in doctor."""
    doctor = _doctor_for_user(request.user)
    appointment = get_object_or_404(
        Appointment,
        pk=appointment_id,
        doctor=doctor,
    )

    updated = Appointment.objects.filter(
        pk=appointment.pk,
        doctor=doctor,
        status="PENDING",
    ).update(status="CONFIRMED")

    if updated:
        appointment.refresh_from_db()
        doctor_name = appointment.doctor.user.get_full_name().strip() or appointment.doctor.user.username
        AppointmentNotification.objects.create(
            recipient=appointment.patient.user,
            appointment=appointment,
            event_type="CONFIRMED",
            message=(
                f"دکتر {doctor_name} درخواست نوبت شما در تاریخ "
                f"{appointment.appointment_date:%Y/%m/%d} ساعت "
                f"{appointment.appointment_time:%H:%M} را تأیید کرد."
            ),
        )
        messages.success(request, "نوبت با موفقیت تأیید شد و اعلان آن برای بیمار ثبت شد.")
    else:
        messages.warning(request, "این درخواست قبلاً بررسی شده و دیگر در انتظار تأیید نیست.")

    return redirect("bookings:doctor_appointments")


@login_required
@require_POST
@transaction.atomic
def reject_doctor_appointment(request, appointment_id):
    """Reject a pending appointment belonging to the logged-in doctor."""
    doctor = _doctor_for_user(request.user)
    appointment = get_object_or_404(
        Appointment,
        pk=appointment_id,
        doctor=doctor,
    )

    updated = Appointment.objects.filter(
        pk=appointment.pk,
        doctor=doctor,
        status="PENDING",
    ).update(status="REJECTED")

    if updated:
        appointment.refresh_from_db()
        doctor_name = appointment.doctor.user.get_full_name().strip() or appointment.doctor.user.username
        AppointmentNotification.objects.create(
            recipient=appointment.patient.user,
            appointment=appointment,
            event_type="REJECTED",
            message=(
                f"دکتر {doctor_name} درخواست نوبت شما در تاریخ "
                f"{appointment.appointment_date:%Y/%m/%d} ساعت "
                f"{appointment.appointment_time:%H:%M} را رد کرد. "
                "می‌توانید زمان دیگری را انتخاب کنید."
            ),
        )
        messages.success(request, "درخواست رد شد و اعلان آن برای بیمار ثبت شد.")
    else:
        messages.warning(request, "این درخواست قبلاً بررسی شده و دیگر در انتظار تأیید نیست.")

    return redirect("bookings:doctor_appointments")


@login_required
def patient_notifications(request):
    """Show only in-site notifications belonging to the logged-in patient."""
    patient_exists = Patient.objects.filter(user=request.user).exists()
    if not patient_exists:
        messages.error(request, "این بخش فقط برای حساب‌های بیمار در دسترس است.")
        if Doctor.objects.filter(user=request.user).exists():
            return redirect("bookings:doctor_dashboard")
        return redirect("accounts:login")

    notifications = AppointmentNotification.objects.filter(
        recipient=request.user
    ).select_related("appointment__doctor__user").order_by("-created_at")
    return render(
        request,
        "bookings/patient_notifications.html",
        {"notifications": notifications},
    )


@login_required
@require_POST
def open_patient_notification(request, notification_id):
    """Mark an owned notification as read and open its appointment details."""
    notification = get_object_or_404(
        AppointmentNotification.objects.select_related("appointment"),
        pk=notification_id,
        recipient=request.user,
    )
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return redirect("bookings:success", appointment_id=notification.appointment_id)
