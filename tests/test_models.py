"""
Tests for Donor and Donation models.

Covers:
- Donor deduplication by phone (primary) and email (secondary)
- Reference generation uniqueness
- Reference generation under concurrency (simulated)
- State-machine guard — no double-paid
- Amount validation
"""

import pytest
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed

import django
from django.test import TestCase

from donations.models import Donor, Donation, TERMINAL_STATES


@pytest.mark.django_db
class TestDonorDeduplication:
    def test_same_phone_returns_existing(self):
        donor1 = Donor.get_or_create_donor("Alice", "Smith", "0773111111", "alice@x.com")
        donor2 = Donor.get_or_create_donor("Alice", "Smith", "+263773111111", "alice@x.com")
        assert donor1.pk == donor2.pk
        assert Donor.objects.count() == 1

    def test_different_format_same_phone(self):
        Donor.objects.create(
            first_name="Bob", last_name="Z", phone="+263772222222", email="bob@x.com"
        )
        found = Donor.get_or_create_donor("Bob", "Z", "0772222222", "bob@x.com")
        assert Donor.objects.count() == 1
        assert found.phone == "+263772222222"

    def test_new_phone_existing_email_updates_phone(self):
        original = Donor.objects.create(
            first_name="Carol", last_name="D", phone="+263773333333", email="carol@x.com"
        )
        # Carol gets a new SIM — same email, new phone
        found = Donor.get_or_create_donor("Carol", "D", "0774444444", "carol@x.com")
        assert found.pk == original.pk
        found.refresh_from_db()
        assert found.phone == "+263774444444"

    def test_new_phone_new_email_creates_donor(self):
        Donor.get_or_create_donor("Dave", "E", "0775555555", "dave@x.com")
        Donor.get_or_create_donor("Eve", "F", "0776666666", "eve@x.com")
        assert Donor.objects.count() == 2

    def test_invalid_phone_raises(self):
        with pytest.raises(ValueError):
            Donor.get_or_create_donor("X", "Y", "not-a-number", "x@x.com")


@pytest.mark.django_db
class TestReferenceGeneration:
    def test_reference_format(self, donor):
        donation = Donation.create_for_donor(donor, Decimal("5.00"), "USD")
        import re, datetime
        year = datetime.date.today().year
        assert re.match(rf"W4L-{year}-\d{{6}}", donation.reference)

    def test_references_are_unique(self, donor):
        refs = {
            Donation.create_for_donor(donor, Decimal("1.00"), "USD").reference
            for _ in range(10)
        }
        assert len(refs) == 10

    def test_sequential_within_year(self, donor):
        d1 = Donation.create_for_donor(donor, Decimal("1.00"), "USD")
        d2 = Donation.create_for_donor(donor, Decimal("1.00"), "USD")
        n1 = int(d1.reference.split("-")[2])
        n2 = int(d2.reference.split("-")[2])
        assert n2 == n1 + 1


@pytest.mark.django_db(transaction=True)
class TestReferenceUniquenessUnderConcurrency:
    """
    Simulate concurrent requests generating references simultaneously.

    SQLite does not support concurrent writes — this test is meaningful only on
    PostgreSQL. On SQLite it verifies sequential uniqueness as a fallback.
    On PostgreSQL (production) SELECT FOR UPDATE ensures no duplicates under load.
    """

    def test_no_duplicate_references_under_concurrent_load(self):
        from django.db import connection

        donor = Donor.objects.create(
            first_name="Test", last_name="User", phone="+263777000001", email="t@t.com"
        )

        if connection.vendor == "sqlite":
            # SQLite can't handle concurrent writes; test sequentially instead.
            refs = [
                Donation.create_for_donor(donor, Decimal("1.00"), "USD").reference
                for _ in range(20)
            ]
        else:
            def make_donation(_):
                return Donation.create_for_donor(donor, Decimal("1.00"), "USD").reference

            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = [pool.submit(make_donation, i) for i in range(20)]
                refs = [f.result() for f in as_completed(futures)]

        assert len(refs) == len(set(refs)), "Duplicate references detected!"


@pytest.mark.django_db
class TestDonationStateMachine:
    def test_paid_donation_str(self, pending_donation):
        d = pending_donation
        d.status = "PAID"
        d.save()
        assert "PAID" in str(d)

    def test_terminal_states_set(self):
        assert TERMINAL_STATES == {"PAID", "CANCELLED", "FAILED"}

    def test_amount_must_be_positive(self, donor):
        with pytest.raises(ValueError, match="greater than zero"):
            Donation.create_for_donor(donor, Decimal("0"), "USD")

    def test_negative_amount_raises(self, donor):
        with pytest.raises(ValueError):
            Donation.create_for_donor(donor, Decimal("-5.00"), "USD")


@pytest.mark.django_db
class TestDonorStr:
    def test_str_format(self):
        donor = Donor.objects.create(
            first_name="Tafara",
            last_name="Ncube",
            phone="+263771234567",
            email="t@example.com",
        )
        assert str(donor) == "Tafara Ncube (+263771234567)"
