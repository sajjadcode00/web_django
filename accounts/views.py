from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import PatientRegistrationForm
from .models import Doctor


def home(request):
    """Send visitors to login and authenticated users to the doctor directory."""
    if request.user.is_authenticated:
        return redirect("accounts:doctor_list")
    return redirect("accounts:login")


def register(request):
    """Register a patient account, then ask the user to log in."""
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "ثبت‌نام شما با موفقیت انجام شد. حالا با نام کاربری و رمز عبورتان وارد شوید.",
            )
            return redirect("accounts:login")
    else:
        form = PatientRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    """Keep the phase-one dashboard URL working, but open the doctor directory."""
    return redirect("accounts:doctor_list")


@login_required
def doctor_list(request):
    """Display active doctors with their specialty and clinic."""
    doctors = (
        Doctor.objects.filter(user__is_active=True)
        .select_related("user", "clinic")
        .order_by("user__last_name", "user__first_name")
    )

    return render(
        request,
        "accounts/doctor_list.html",
        {"doctors": doctors, "doctor_count": doctors.count()},
    )
