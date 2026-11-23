from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Patient


# Convert Persian and Arabic digits to ASCII so that users can type either form.
DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


class PatientRegistrationForm(UserCreationForm):
    """Create a Django User and its related Patient profile together."""

    national_id = forms.CharField(
        label="کد ملی",
        max_length=10,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "کد ملی ۱۰ رقمی",
                "inputmode": "numeric",
                "autocomplete": "off",
            }
        ),
    )
    phone_number = forms.CharField(
        label="شماره موبایل",
        max_length=11,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "مثلاً 09123456789",
                "inputmode": "tel",
                "autocomplete": "tel",
                "dir": "ltr",
            }
        ),
    )

    error_messages = {
        "password_mismatch": "رمز عبور و تکرار آن یکسان نیستند.",
    }

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["first_name"].label = "نام"
        self.fields["first_name"].required = True
        self.fields["first_name"].widget.attrs.update(
            {"class": "form-input", "placeholder": "نام خود را وارد کنید", "autocomplete": "given-name"}
        )

        self.fields["last_name"].label = "نام خانوادگی"
        self.fields["last_name"].required = True
        self.fields["last_name"].widget.attrs.update(
            {"class": "form-input", "placeholder": "نام خانوادگی خود را وارد کنید", "autocomplete": "family-name"}
        )

        self.fields["username"].label = "نام کاربری"
        self.fields["username"].help_text = "برای ورودهای بعدی از این نام کاربری استفاده می‌کنید."
        self.fields["username"].widget.attrs.update(
            {"class": "form-input", "placeholder": "یک نام کاربری انتخاب کنید", "autocomplete": "username", "dir": "ltr"}
        )

        self.fields["password1"].label = "رمز عبور"
        self.fields["password1"].help_text = "از رمز عبور قوی و غیرقابل حدس استفاده کنید."
        self.fields["password1"].widget.attrs.update(
            {"class": "form-input", "placeholder": "رمز عبور", "autocomplete": "new-password", "dir": "ltr"}
        )

        self.fields["password2"].label = "تکرار رمز عبور"
        self.fields["password2"].help_text = "رمز عبور را دوباره وارد کنید."
        self.fields["password2"].widget.attrs.update(
            {"class": "form-input", "placeholder": "تکرار رمز عبور", "autocomplete": "new-password", "dir": "ltr"}
        )

        # Keep the form in a predictable order instead of relying on field declaration order.
        self.order_fields(
            [
                "first_name",
                "last_name",
                "username",
                "national_id",
                "phone_number",
                "password1",
                "password2",
            ]
        )

    def clean_national_id(self):
        value = self.cleaned_data["national_id"].translate(DIGIT_TRANSLATION)

        if not value.isdigit() or len(value) != 10:
            raise ValidationError("کد ملی باید دقیقاً ۱۰ رقم باشد.")

        if Patient.objects.filter(national_id=value).exists():
            raise ValidationError("با این کد ملی قبلاً حساب کاربری ساخته شده است.")

        return value

    def clean_phone_number(self):
        value = self.cleaned_data["phone_number"].translate(DIGIT_TRANSLATION)

        if not value.isdigit() or len(value) != 11:
            raise ValidationError("شماره موبایل باید دقیقاً ۱۱ رقم باشد.")

        return value

    def save(self, commit=True):
        """Save User and Patient atomically; never store a plain-text password."""
        user = super().save(commit=False)

        if commit:
            with transaction.atomic():
                user.save()
                Patient.objects.create(
                    user=user,
                    national_id=self.cleaned_data["national_id"],
                    phone_number=self.cleaned_data["phone_number"],
                )

        return user


class PatientAuthenticationForm(AuthenticationForm):
    """Persian labels and styling for Django's standard authentication form."""

    error_messages = {
        "invalid_login": "نام کاربری یا رمز عبور اشتباه است.",
        "inactive": "این حساب کاربری غیرفعال است.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "نام کاربری"
        self.fields["username"].widget.attrs.update(
            {"class": "form-input", "placeholder": "نام کاربری خود را وارد کنید", "autocomplete": "username", "dir": "ltr"}
        )
        self.fields["password"].label = "رمز عبور"
        self.fields["password"].widget.attrs.update(
            {"class": "form-input", "placeholder": "رمز عبور خود را وارد کنید", "autocomplete": "current-password", "dir": "ltr"}
        )
