"""
Utility helpers for the donations app.

Phone normalisation rules (Zimbabwe):
  - Strip all spaces, dashes, parentheses.
  - Accept leading "0"  → replace with "+263".
  - Accept leading "263" → prepend "+".
  - Accept leading "+263" → already canonical, just clean whitespace.
  - Anything else is rejected with ValueError.
  - Final form must match +263[7][0-9]{8}  (mobile) or +263[2-9][0-9]{6,8} (fixed).
    We enforce the pattern +263 followed by 9 digits to cover all current formats.
"""

import re

_ZW_CANONICAL = re.compile(r"^\+263\d{9}$")


def normalize_phone(raw: str) -> str:
    """
    Normalise a Zimbabwean phone number to +263XXXXXXXXX (12 chars total).

    Accepted input forms:
        0773123456   →  +263773123456
        263773123456 →  +263773123456
        +263773123456 → +263773123456
        077 312 3456 → +263773123456   (spaces stripped)

    Raises ValueError for numbers that cannot be normalised or are clearly invalid.
    """
    if not raw:
        raise ValueError("Phone number cannot be empty.")

    # Strip visual separators
    cleaned = re.sub(r"[\s\-().]+", "", raw)

    if cleaned.startswith("+263"):
        normalised = cleaned
    elif cleaned.startswith("263"):
        normalised = "+" + cleaned
    elif cleaned.startswith("0"):
        normalised = "+263" + cleaned[1:]
    else:
        raise ValueError(
            f"Cannot normalise phone number '{raw}': expected Zimbabwean format "
            f"(0XX…, 263XX…, or +263XX…)."
        )

    if not _ZW_CANONICAL.match(normalised):
        raise ValueError(
            f"Phone number '{raw}' does not match expected Zimbabwean format "
            f"+263XXXXXXXXX (9 digits after country code). Got '{normalised}'."
        )

    return normalised
