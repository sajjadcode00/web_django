from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import (
    AccountAuthenticationForm,
    DoctorRegistrationForm,
    PatientRegistrationForm,
)
from .models import Doctor, Patient


class AccountLoginView(LoginView):
    """Shared login form that redirects doctors and patients to their own workspace."""

    template_name = "accounts/login.html"
    authentication_form = AccountAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        requested_url = self.get_redirect_url()
        if requested_url:
            return requested_url
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return reverse("admin:index")
        if Doctor.objects.filter(user=user).exists():
            return reverse("bookings:doctor_dashboard")
        return reverse("accounts:doctor_list")


def home(request):
    """Send visitors to the correct workspace based on their account profile."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.is_superuser or request.user.is_staff:
        return redirect("admin:index")
    if Doctor.objects.filter(user=request.user).exists():
        return redirect("bookings:doctor_dashboard")
    return redirect("accounts:doctor_list")


def register(request):
    """Register a patient account, then ask the user to log in."""
    if request.user.is_authenticated:
        return redirect("home")

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


def doctor_register(request):
    """Register a doctor profile in an inactive state for administrator verification."""
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = DoctorRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "درخواست ثبت‌نام پزشک دریافت شد. پس از بررسی اطلاعات و فعال‌سازی حساب توسط مدیر، امکان ورود خواهید داشت.",
            )
            return redirect("accounts:login")
    else:
        form = DoctorRegistrationForm()

    return render(request, "accounts/doctor_register.html", {"form": form})


@require_POST
def logout_view(request):
    """Log out the current user using a CSRF-protected POST request."""
    logout(request)
    messages.success(request, "با موفقیت از حساب کاربری خارج شدید.")
    return redirect("accounts:login")


@login_required
def dashboard(request):
    """Compatibility route: doctors go to their portal, other signed-in users to doctors."""
    if Doctor.objects.filter(user=request.user).exists():
        return redirect("bookings:doctor_dashboard")
    return redirect("accounts:doctor_list")


@login_required
def doctor_list(request):
    """Display active doctors with optional name and specialty search filters."""
    doctors = Doctor.objects.filter(user__is_active=True).select_related("user", "clinic")
    search_query = request.GET.get("q", "").strip()
    selected_specialty = request.GET.get("specialty", "").strip()

    if search_query:
        for term in search_query.split():
            doctors = doctors.filter(
                Q(user__first_name__icontains=term)
                | Q(user__last_name__icontains=term)
                | Q(user__username__icontains=term)
                | Q(specialty__icontains=term)
            )
    if selected_specialty:
        doctors = doctors.filter(specialty=selected_specialty)

    doctors = doctors.order_by("user__last_name", "user__first_name")
    specialties = (
        Doctor.objects.filter(user__is_active=True)
        .order_by()
        .values_list("specialty", flat=True)
        .distinct()
    )

    return render(
        request,
        "accounts/doctor_list.html",
        {
            "doctors": doctors,
            "doctor_count": doctors.count(),
            "search_query": search_query,
            "selected_specialty": selected_specialty,
            "specialties": specialties,
        },
    )


@login_required
def doctor_detail(request, doctor_id):
    """Show the profile of an active doctor."""
    doctor = get_object_or_404(
        Doctor.objects.filter(user__is_active=True).select_related("user", "clinic"),
        pk=doctor_id,
    )
    return render(
        request,
        "accounts/doctor_detail.html",
        {"doctor": doctor, "is_patient": Patient.objects.filter(user=request.user).exists()},
    )
