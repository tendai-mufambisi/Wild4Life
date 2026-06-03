"""
Paynow payment gateway integration for Wild4Life donations.

THIS IS THE ONLY FILE IN THE CODEBASE THAT MAY IMPORT OR CALL THE `paynow` SDK.
All gateway interactions are isolated here so that SDK changes require edits
in exactly one place.

Flow used: WEB / HOSTED-PAGE (redirect).
  1. initiate_payment()  → creates a Paynow payment and returns the redirect URL.
  2. verify_payment()    → polls Paynow via the stored poll URL and updates the
                           Donation status + triggers the confirmation email.

SDK reference (paynow 1.0.x):
  from paynow import Paynow
  paynow = Paynow(integration_id, integration_key, return_url, result_url)
  payment = paynow.create_payment(reference, email)
  payment.add(description, amount)
  response = paynow.send(payment)          # WEB flow
  response.success   -> bool
  response.redirect_url -> str
  response.poll_url  -> str
  status = paynow.check_transaction_status(poll_url)
  status.paid        -> bool
"""

import logging
from typing import Optional

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_paynow_client():
    """
    Build a configured Paynow client from Django settings.

    Lazy import keeps the SDK contained in this module. Called once per
    request rather than at import time so settings are always fully loaded.
    """
    from paynow import Paynow  # noqa: PLC0415 — intentional local import

    return Paynow(
        settings.PAYNOW_INTEGRATION_ID,
        settings.PAYNOW_INTEGRATION_KEY,
        settings.PAYNOW_RETURN_URL,
        settings.PAYNOW_RESULT_URL,
    )


def initiate_payment(donation) -> Optional[str]:
    """
    Create a Paynow payment session for *donation* and return the redirect URL.

    On success, saves poll_url to donation (caller must save the donation object).
    On failure, sets donation.status = 'FAILED', logs the error, and returns None.

    Args:
        donation: A Donation instance with status == 'PENDING'. Must have a
                  related Donor with a valid email.

    Returns:
        The Paynow hosted-page redirect URL as a string, or None on failure.
    """
    paynow = _get_paynow_client()

    try:
        payment = paynow.create_payment(donation.reference, donation.donor.email)
        payment.add("Donation to Wild4Life", float(donation.amount))
        response = paynow.send(payment)
    except Exception:
        logger.exception(
            "Paynow SDK raised an unexpected exception while initiating payment "
            "for donation %s", donation.reference
        )
        donation.status = "FAILED"
        donation.save(update_fields=["status"])
        return None

    if not response.success:
        logger.error(
            "Paynow initiation failed for donation %s. "
            "SDK response indicated failure (response.success=False).",
            donation.reference,
        )
        donation.status = "FAILED"
        donation.save(update_fields=["status"])
        return None

    donation.paynow_poll_url = response.poll_url
    # response.hash is Paynow's own transaction ref — store if available
    if hasattr(response, "hash") and response.hash:
        donation.paynow_reference = response.hash
    donation.save(update_fields=["paynow_poll_url", "paynow_reference"])

    logger.info(
        "Paynow payment initiated for donation %s. Redirect: %s",
        donation.reference,
        response.redirect_url,
    )
    return response.redirect_url


def verify_payment(donation) -> str:
    """
    Poll Paynow for the current transaction status and update the Donation record.

    Idempotent: if donation is already in a terminal state (PAID/FAILED/CANCELLED)
    this function returns the current status immediately without polling Paynow,
    so duplicate IPN calls are safe.

    On confirmed PAID, sets paid_at and triggers a thank-you email.
    Email failures are logged but never allowed to bubble up — payment confirmation
    must not be blocked by an SMTP outage.

    Args:
        donation: A Donation instance with paynow_poll_url populated.

    Returns:
        The (possibly updated) donation.status string.
    """
    from .models import TERMINAL_STATES  # avoid circular import at module level

    # Idempotency guard — never re-process a terminal state.
    if donation.status in TERMINAL_STATES:
        logger.debug(
            "verify_payment called on donation %s which is already %s — skipping poll.",
            donation.reference,
            donation.status,
        )
        return donation.status

    if not donation.paynow_poll_url:
        logger.warning(
            "Cannot verify donation %s: no poll URL stored.", donation.reference
        )
        return donation.status

    paynow = _get_paynow_client()

    try:
        status = paynow.check_transaction_status(donation.paynow_poll_url)
    except Exception:
        logger.exception(
            "Paynow SDK raised an exception while checking status for donation %s",
            donation.reference,
        )
        return donation.status

    if status.paid:
        donation.status  = "PAID"
        donation.paid_at = timezone.now()
        donation.save(update_fields=["status", "paid_at"])
        logger.info("Donation %s confirmed PAID.", donation.reference)
        _send_confirmation_email(donation)
    else:
        # Paynow may also return "cancelled" or other non-paid statuses.
        # We leave PENDING until we receive a definitive paid or failed signal.
        # A separate scheduled task could time out stale PENDING donations.
        logger.info(
            "Donation %s polled: not yet paid (Paynow status object received).",
            donation.reference,
        )

    return donation.status


def _send_confirmation_email(donation) -> None:
    """
    Send a thank-you email to the donor with their reference code.

    Wrapped in a broad try/except so that an SMTP failure never prevents the
    payment record from being updated. Failures are logged at ERROR level so
    they appear in monitoring without crashing the request.
    """
    from django.core.mail import send_mail  # noqa: PLC0415

    subject = f"Thank you for your donation — {donation.reference}"
    body = (
        f"Dear {donation.donor.first_name},\n\n"
        f"Thank you for your generous donation to Wild4Life Organisation.\n\n"
        f"Your donation details:\n"
        f"  Reference : {donation.reference}\n"
        f"  Amount    : {donation.currency} {donation.amount}\n"
        f"  Date      : {donation.paid_at.strftime('%d %B %Y') if donation.paid_at else 'N/A'}\n\n"
        f"Please keep this reference code for your records. "
        f"You may need it if you contact us about this donation.\n\n"
        f"Wild4Life Organisation\n"
        f"Protecting Zimbabwe's wildlife — one donation at a time.\n"
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[donation.donor.email],
            fail_silently=False,
        )
        logger.info(
            "Confirmation email sent to %s for donation %s.",
            donation.donor.email,
            donation.reference,
        )
    except Exception:
        logger.exception(
            "Failed to send confirmation email for donation %s to %s. "
            "Payment record is still updated — this is an email-only failure.",
            donation.reference,
            donation.donor.email,
        )
