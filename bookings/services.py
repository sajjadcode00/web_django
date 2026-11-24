from datetime import datetime, timedelta

from django.utils import timezone

from .models import Appointment, DoctorSchedule


def available_slots_for(doctor, appointment_date):
    """Return free appointment start times generated from a doctor's weekly schedule."""
    schedules = DoctorSchedule.objects.filter(
        doctor=doctor,
        weekday=appointment_date.weekday(),
        is_active=True,
    ).order_by("start_time")

    occupied = set(
        Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
        )
        .exclude(status__in=("CANCELLED", "REJECTED"))
        .values_list("appointment_time", flat=True)
    )

    now = timezone.localtime()
    is_today = appointment_date == timezone.localdate()
    free_slots = set()

    for schedule in schedules:
        current = datetime.combine(appointment_date, schedule.start_time)
        closing = datetime.combine(appointment_date, schedule.end_time)
        duration = timedelta(minutes=schedule.slot_duration_minutes)

        while current + duration <= closing:
            slot = current.time().replace(second=0, microsecond=0)
            slot_datetime = timezone.make_aware(current, timezone.get_current_timezone())
            if slot not in occupied and (not is_today or slot_datetime > now):
                free_slots.add(slot)
            current += duration

    return sorted(free_slots)
