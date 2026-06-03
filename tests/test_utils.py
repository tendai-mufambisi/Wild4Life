"""Tests for phone number normalisation utility."""

import pytest
from donations.utils import normalize_phone


class TestNormalizePhone:
    # ── Valid inputs ──────────────────────────────────────────────────────────

    def test_local_zero_prefix(self):
        assert normalize_phone("0773123456") == "+263773123456"

    def test_local_with_spaces(self):
        assert normalize_phone("077 312 3456") == "+263773123456"

    def test_263_prefix(self):
        assert normalize_phone("263773123456") == "+263773123456"

    def test_plus263_prefix(self):
        assert normalize_phone("+263773123456") == "+263773123456"

    def test_plus263_with_spaces(self):
        assert normalize_phone("+263 773 123 456") == "+263773123456"

    def test_netone_number(self):
        assert normalize_phone("0712345678") == "+263712345678"

    def test_telecel_number(self):
        assert normalize_phone("0733456789") == "+263733456789"

    def test_econet_078(self):
        assert normalize_phone("0783456789") == "+263783456789"

    def test_dashes_stripped(self):
        assert normalize_phone("077-312-3456") == "+263773123456"

    def test_parentheses_stripped(self):
        assert normalize_phone("(0773) 123456") == "+263773123456"

    def test_already_canonical_unchanged(self):
        number = "+263773123456"
        assert normalize_phone(number) == number

    # ── Invalid inputs ────────────────────────────────────────────────────────

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_phone("")

    def test_uk_number_raises(self):
        with pytest.raises(ValueError):
            normalize_phone("+447700900000")

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            normalize_phone("077123")

    def test_letters_raises(self):
        with pytest.raises(ValueError):
            normalize_phone("077abc1234")

    def test_no_prefix_raises(self):
        with pytest.raises(ValueError):
            normalize_phone("773123456")
