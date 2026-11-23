from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Doctor, Patient

from .forms import AppointmentBookingForm
from .models import Appointment


@login_required
def create_appointment(request, doctor_id):
    """Create a pending appointment for the patient who is currently logged in."""
    doctor = get_object_or_404(
        Doctor.objects.select_related("user", "clinic"),
        pk=doctor_id,
        user__is_active=True,
    )

    patient = Patient.objects.filter(user=request.user).first()
    if patient is None:
        messages.error(
            request,
            "رزرو نوبت فقط با حساب کاربری بیمار امکان‌پذیر است.",
        )
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
                # The database constraint is the final guard against two requests
                # reserving the same doctor/date/time at nearly the same moment.
                form.add_error(
                    "appointment_time",
                    "این زمان همین الان توسط شخص دیگری رزرو شد. لطفاً زمان دیگری انتخاب کنید.",
                )
            else:
                messages.success(request, "درخواست نوبت شما با موفقیت ثبت شد.")
                return redirect("bookings:success", appointment_id=appointment.pk)
    else:
        form = AppointmentBookingForm(doctor=doctor)

    return render(
        request,
        "bookings/appointment_form.html",
        {"form": form, "doctor": doctor},
    )


@login_required
def appointment_success(request, appointment_id):
    """Show a booking confirmation only to the patient who owns the appointment."""
    patient = get_object_or_404(Patient, user=request.user)
    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "doctor__user",
            "doctor__clinic",
            "patient__user",
        ),
        pk=appointment_id,
        patient=patient,
    )

    return render(
        request,
        "bookings/appointment_success.html",
        {"appointment": appointment},
    )
