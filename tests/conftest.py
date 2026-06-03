"""
pytest-django configuration and shared fixtures.
"""

import pytest
from decimal import Decimal

from donations.models import Donor, Donation


@pytest.fixture
def donor(db):
    return Donor.objects.create(
        first_name="Tendai",
        last_name="Moyo",
        phone="+263773123456",
        email="tendai@example.com",
    )


@pytest.fixture
def pending_donation(db, donor):
    return Donation.create_for_donor(
        donor=donor,
        amount=Decimal("10.00"),
        currency="USD",
    )
