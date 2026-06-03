from decimal import Decimal, InvalidOperation

from django import forms
from django.conf import settings

from .utils import normalize_phone


class DonationForm(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        label="First name",
        widget=forms.TextInput(attrs={"autocomplete": "given-name", "placeholder": "Tendai"}),
    )
    last_name = forms.CharField(
        max_length=100,
        label="Last name",
        widget=forms.TextInput(attrs={"autocomplete": "family-name", "placeholder": "Moyo"}),
    )
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
    )
    phone = forms.CharField(
        max_length=20,
        label="Mobile number",
        widget=forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "0773 123 456"}),
        help_text="Zimbabwean mobile number, e.g. 0773 123 456 or +263773123456",
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("1.00"),
        label="Donation amount",
        widget=forms.NumberInput(attrs={"placeholder": "10.00", "step": "0.01", "min": "1"}),
    )
    currency = forms.ChoiceField(
        choices=[("USD", "USD — US Dollar"), ("ZWG", "ZWG — Zimbabwe Gold")],
        initial=settings.DEFAULT_CURRENCY,
        label="Currency",
    )

    def clean_phone(self) -> str:
        raw = self.cleaned_data["phone"]
        try:
            return normalize_phone(raw)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def clean_amount(self) -> Decimal:
        amount = self.cleaned_data.get("amount")
        if amount is None:
            raise forms.ValidationError("Please enter a valid donation amount.")
        if amount <= Decimal("0"):
            raise forms.ValidationError("Donation amount must be greater than zero.")
        return amount
