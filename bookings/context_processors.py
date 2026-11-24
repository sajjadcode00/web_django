from accounts.models import Patient

from .models import AppointmentNotification


def patient_notification_summary(request):
    """Expose the patient's unread notification count to shared templates."""
    context = {
        "show_patient_notifications": False,
        "unread_notification_count": 0,
    }

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return context

    if Patient.objects.filter(user_id=user.pk).exists():
        context["show_patient_notifications"] = True
        context["unread_notification_count"] = AppointmentNotification.objects.filter(
            recipient_id=user.pk,
            is_read=False,
        ).count()

    return context
