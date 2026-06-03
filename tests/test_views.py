"""
Tests for donation views.

Uses Django test client. Paynow service is mocked so no real Paynow calls are made.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from donations.models import Donor, Donation


VALID_FORM_DATA = {
    "first_name": "Blessing",
    "last_name":  "Mutasa",
    "email":      "blessing@example.com",
    "phone":      "0773999888",
    "amount":     "20.00",
    "currency":   "USD",
}


@pytest.mark.django_db
class TestDonateView:
    def test_get_renders_form(self, client):
        response = client.get(reverse("donations:donate"))
        assert response.status_code == 200
        assert b"Donate" in response.content

    def test_post_valid_redirects_to_paynow(self, client):
        with patch(
            "donations.views.paynow_service.initiate_payment",
            return_value="https://paynow.co.zw/pay/testtoken",
        ):
            response = client.post(reverse("donations:donate"), VALID_FORM_DATA)

        assert response.status_code == 302
        assert response["Location"] == "https://paynow.co.zw/pay/testtoken"
        assert Donation.objects.count() == 1
        assert Donor.objects.count() == 1

    def test_post_invalid_phone_shows_errors(self, client):
        data = {**VALID_FORM_DATA, "phone": "not-a-phone"}
        response = client.post(reverse("donations:donate"), data)
        assert response.status_code == 200
        assert Donation.objects.count() == 0

    def test_post_zero_amount_shows_errors(self, client):
        data = {**VALID_FORM_DATA, "amount": "0"}
        response = client.post(reverse("donations:donate"), data)
        assert response.status_code == 200
        assert Donation.objects.count() == 0

    def test_post_negative_amount_shows_errors(self, client):
        data = {**VALID_FORM_DATA, "amount": "-5"}
        response = client.post(reverse("donations:donate"), data)
        assert response.status_code == 200
        assert Donation.objects.count() == 0

    def test_post_paynow_failure_shows_error_page(self, client):
        with patch(
            "donations.views.paynow_service.initiate_payment",
            return_value=None,
        ):
            response = client.post(reverse("donations:donate"), VALID_FORM_DATA)

        assert response.status_code == 502
        # Donation is created but marked FAILED
        donation = Donation.objects.get()
        assert donation.status == "FAILED"

    def test_post_is_csrf_protected(self, client):
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(reverse("donations:donate"), VALID_FORM_DATA)
        assert response.status_code == 403


@pytest.mark.django_db
class TestDonationReturnView:
    def _create_paid_donation(self):
        donor = Donor.objects.create(
            first_name="Rudo", last_name="T", phone="+263771122334", email="r@x.com"
        )
        d = Donation.create_for_donor(donor, Decimal("10.00"), "USD")
        d.status = "PAID"
        d.save()
        return d

    def test_return_with_valid_reference(self, client):
        donation = self._create_paid_donation()
        with patch("donations.views.paynow_service.verify_payment", return_value="PAID"):
            response = client.get(
                reverse("donations:donation_return"),
                {"reference": donation.reference},
            )
        assert response.status_code == 200
        assert donation.reference.encode() in response.content

    def test_return_without_reference_renders_generic(self, client):
        response = client.get(reverse("donations:donation_return"))
        assert response.status_code == 200

    def test_return_unknown_reference_returns_404_page(self, client):
        response = client.get(
            reverse("donations:donation_return"),
            {"reference": "W4L-9999-000001"},
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestPaynowResultView:
    def _pending_donation(self):
        donor = Donor.objects.create(
            first_name="Test", last_name="IPN", phone="+263773000111", email="ipn@x.com"
        )
        return Donation.create_for_donor(donor, Decimal("5.00"), "USD")

    def test_ipn_calls_verify_and_returns_200(self, client):
        donation = self._pending_donation()
        with patch("donations.views.paynow_service.verify_payment") as mock_verify:
            response = client.post(
                reverse("donations:paynow_result"),
                {"reference": donation.reference},
            )
        assert response.status_code == 200
        mock_verify.assert_called_once_with(donation)

    def test_ipn_no_reference_returns_200(self, client):
        response = client.post(reverse("donations:paynow_result"), {})
        assert response.status_code == 200

    def test_ipn_unknown_reference_returns_200(self, client):
        response = client.post(
            reverse("donations:paynow_result"),
            {"reference": "W4L-0000-999999"},
        )
        assert response.status_code == 200

    def test_ipn_terminal_state_skips_verify(self, client):
        donation = self._pending_donation()
        donation.status = "PAID"
        donation.save()

        with patch("donations.views.paynow_service.verify_payment") as mock_verify:
            response = client.post(
                reverse("donations:paynow_result"),
                {"reference": donation.reference},
            )

        assert response.status_code == 200
        mock_verify.assert_not_called()

    def test_ipn_is_csrf_exempt(self, client):
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        donation = self._pending_donation()
        with patch("donations.views.paynow_service.verify_payment"):
            response = csrf_client.post(
                reverse("donations:paynow_result"),
                {"reference": donation.reference},
            )
        assert response.status_code == 200
