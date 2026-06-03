"""
Tests for paynow_service.py.

Paynow SDK is fully mocked — no network calls are made.
Tests verify correct orchestration logic, error handling, and idempotency.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from donations.models import Donor, Donation
from donations import paynow_service


def _make_donor(db):
    return Donor.objects.create(
        first_name="Rudo",
        last_name="Chikwanda",
        phone="+263778888888",
        email="rudo@example.com",
    )


def _make_donation(donor):
    return Donation.create_for_donor(donor, Decimal("25.00"), "USD")


@pytest.mark.django_db
class TestInitiatePayment:
    def test_success_returns_redirect_url(self, db):
        donor    = _make_donor(db)
        donation = _make_donation(donor)

        mock_response            = MagicMock()
        mock_response.success    = True
        mock_response.redirect_url = "https://paynow.co.zw/pay/abc123"
        mock_response.poll_url   = "https://paynow.co.zw/poll/abc123"
        mock_response.hash       = "abc123"

        mock_paynow              = MagicMock()
        mock_paynow.send.return_value = mock_response

        mock_payment             = MagicMock()
        mock_paynow.create_payment.return_value = mock_payment

        with patch("donations.paynow_service._get_paynow_client", return_value=mock_paynow):
            url = paynow_service.initiate_payment(donation)

        assert url == "https://paynow.co.zw/pay/abc123"
        donation.refresh_from_db()
        assert donation.paynow_poll_url == "https://paynow.co.zw/poll/abc123"
        assert donation.status == "PENDING"

    def test_failure_marks_donation_failed(self, db):
        donor    = _make_donor(db)
        donation = _make_donation(donor)

        mock_response         = MagicMock()
        mock_response.success = False

        mock_paynow           = MagicMock()
        mock_paynow.send.return_value = mock_response
        mock_paynow.create_payment.return_value = MagicMock()

        with patch("donations.paynow_service._get_paynow_client", return_value=mock_paynow):
            url = paynow_service.initiate_payment(donation)

        assert url is None
        donation.refresh_from_db()
        assert donation.status == "FAILED"

    def test_sdk_exception_marks_donation_failed(self, db):
        donor    = _make_donor(db)
        donation = _make_donation(donor)

        mock_paynow           = MagicMock()
        mock_paynow.create_payment.side_effect = RuntimeError("network down")

        with patch("donations.paynow_service._get_paynow_client", return_value=mock_paynow):
            url = paynow_service.initiate_payment(donation)

        assert url is None
        donation.refresh_from_db()
        assert donation.status == "FAILED"


@pytest.mark.django_db
class TestVerifyPayment:
    def test_paid_status_sets_paid_at(self, db):
        donor    = _make_donor(db)
        donation = _make_donation(donor)
        donation.paynow_poll_url = "https://paynow.co.zw/poll/xyz"
        donation.save()

        mock_status      = MagicMock()
        mock_status.paid = True

        mock_paynow      = MagicMock()
        mock_paynow.check_transaction_status.return_value = mock_status

        with patch("donations.paynow_service._get_paynow_client", return_value=mock_paynow):
            with patch("donations.paynow_service._send_confirmation_email") as mock_email:
                result = paynow_service.verify_payment(donation)

        assert result == "PAID"
        donation.refresh_from_db()
        assert donation.status == "PAID"
        assert donation.paid_at is not None
        mock_email.assert_called_once_with(donation)

    def test_not_paid_leaves_pending(self, db):
        donor    = _make_donor(db)
        donation = _make_donation(donor)
        donation.paynow_poll_url = "https://paynow.co.zw/poll/xyz"
        donation.save()

        mock_status      = MagicMock()
        mock_status.paid = False

        mock_paynow      = MagicMock()
        mock_paynow.check_transaction_status.return_value = mock_status

        with patch("donations.paynow_service._get_paynow_client", return_value=mock_paynow):
            result = paynow_service.verify_payment(donation)

        assert result == "PENDING"
        donation.refresh_from_db()
        assert donation.status == "PENDING"

    def test_idempotency_paid_not_re_processed(self, db):
        """verify_payment on an already-PAID donation must not poll Paynow again."""
        donor    = _make_donor(db)
        donation = _make_donation(donor)
        donation.status = "PAID"
        donation.save()

        mock_paynow = MagicMock()

        with patch("donations.paynow_service._get_paynow_client", return_value=mock_paynow):
            result = paynow_service.verify_payment(donation)

        assert result == "PAID"
        mock_paynow.check_transaction_status.assert_not_called()

    def test_idempotency_failed_not_re_processed(self, db):
        donor    = _make_donor(db)
        donation = _make_donation(donor)
        donation.status = "FAILED"
        donation.save()

        mock_paynow = MagicMock()

        with patch("donations.paynow_service._get_paynow_client", return_value=mock_paynow):
            result = paynow_service.verify_payment(donation)

        assert result == "FAILED"
        mock_paynow.check_transaction_status.assert_not_called()

    def test_no_poll_url_returns_current_status(self, db):
        donor    = _make_donor(db)
        donation = _make_donation(donor)
        # poll_url is blank (not yet set)
        assert donation.paynow_poll_url == ""

        mock_paynow = MagicMock()

        with patch("donations.paynow_service._get_paynow_client", return_value=mock_paynow):
            result = paynow_service.verify_payment(donation)

        assert result == "PENDING"
        mock_paynow.check_transaction_status.assert_not_called()
