from django import forms
from .models import Account, UserAddress
import re


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter password (min 8 characters)",
                "class": "form-control",
            }
        )
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm password",
                "class": "form-control",
            }
        )
    )

    class Meta:
        model = Account
        fields = ["first_name", "last_name", "email", "password"]

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs["placeholder"] = "Enter First Name"
        self.fields["last_name"].widget.attrs["placeholder"] = "Enter Last Name"
        self.fields["email"].widget.attrs["placeholder"] = "Enter Email Address"

        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get("first_name")
        last_name = cleaned_data.get("last_name")
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if first_name and not first_name.isalpha():
            raise forms.ValidationError(
                "First name can contain only letters."
            )

        if last_name and not last_name.isalpha():
            raise forms.ValidationError(
                "Last name can contain only letters."
            )

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match")

            if len(password) < 8:
                raise forms.ValidationError(
                    "Password must be at least 8 characters long."
                )

            if not re.search(r"[A-Z]", password):
                raise forms.ValidationError(
                    "Password must contain at least one uppercase letter."
                )

            if not re.search(r"[a-z]", password):
                raise forms.ValidationError(
                    "Password must contain at least one lowercase letter."
                )

            if not re.search(r"\d", password):
                raise forms.ValidationError(
                    "Password must contain at least one number."
                )

            if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
                raise forms.ValidationError(
                    "Password must contain at least one special character."
                )
        return cleaned_data


class AddressForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        fields = [
            "full_name",
            "phone",
            "address_line",
            "city",
            "state",
            "pincode",
            "address_type",
            "is_default",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            if field != "is_default":
                self.fields[field].widget.attrs["class"] = "form-control"
        self.fields["is_default"].widget.attrs["class"] = "form-check-input"
        self.fields["phone"].widget.attrs["placeholder"] = "e.g. 9876543210"
        self.fields["city"].widget.attrs["placeholder"] = "e.g. Ernakulam"
        self.fields["pincode"].widget.attrs["placeholder"] = "e.g. 689230"
        self.fields["state"].widget.attrs["placeholder"] = "e.g. Kerala"
        self.fields["address_line"].widget.attrs.update(
            {
                "rows": 3,
                "placeholder": "House Name, House Number, Locality"
            })

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if not re.match(r"^[A-Za-z ]+$", full_name):
            raise forms.ValidationError(
                "Full name can contain only letters and spaces."
            )
        return full_name

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone.isdigit():
            raise forms.ValidationError(
                "Phone number must contain only digits."
            )
        if len(phone) != 10:
            raise forms.ValidationError(
                "Phone number must be exactly 10 digits."
            )
        if len(set(phone)) == 1:
            raise forms.ValidationError(
                "Invalid phone number."
            )
        return phone

    def clean_city(self):
        city = self.cleaned_data["city"].strip()
        if not re.match(r"^[A-Za-z ]+$", city):
            raise forms.ValidationError(
                "City can contain only letters and spaces."
            )
        return city

    def clean_state(self):
        state = self.cleaned_data["state"].strip()
        if not re.match(r"^[A-Za-z ]+$", state):
            raise forms.ValidationError(
                "State can contain only letters and spaces."
            )
        return state

    def clean_pincode(self):
        pincode = self.cleaned_data["pincode"].strip()
        if not pincode.isdigit():
            raise forms.ValidationError(
                "Pincode must contain only digits."
            )
        if len(pincode) != 6:
            raise forms.ValidationError(
                "Pincode must be exactly 6 digits."
            )
        return pincode
