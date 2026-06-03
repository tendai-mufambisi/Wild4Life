"""
Views implementing the Wild4Life donation payment flow.

URL map:
  GET/POST /donate/         → donation form
  GET      /donation/return/ → browser return page (cosmetic, polls for status)
  POST     /paynow/result/  → Paynow IPN (server-to-server, CSRF-exempt, source of truth)
"""

import logging
from uuid import UUID

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .forms import DonationForm


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "index.html")
from .models import Donor, Donation, TERMINAL_STATES
from . import paynow_service

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
def donate(request: HttpRequest) -> HttpResponse:
    """
    GET  — render the donation form.
    POST — validate, create donor + donation, initiate Paynow, redirect.
    """
    if request.method == "GET":
        form = DonationForm()
        return render(request, "donations/donate.html", {"form": form})

    form = DonationForm(request.POST)
    if not form.is_valid():
        return render(request, "donations/donate.html", {"form": form})

    data = form.cleaned_data

    try:
        donor = Donor.get_or_create_donor(
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data["phone"],
            email=data["email"],
        )
    except ValueError as exc:
        logger.warning("Donor creation failed: %s", exc)
        return render(
            request,
            "donations/error.html",
            {"message": "We could not process your details. Please check your phone number and try again."},
            status=400,
        )

    donation = Donation.create_for_donor(
        donor=donor,
        amount=data["amount"],
        currency=data["currency"],
    )

    redirect_url = paynow_service.initiate_payment(donation)
    if redirect_url is None:
        logger.error(
            "Paynow initiation returned None for donation %s — showing error page.",
            donation.reference,
        )
        # Ensure status is FAILED even if the service layer didn't save it
        # (e.g. in tests where the service is mocked out entirely).
        if donation.status != "FAILED":
            donation.status = "FAILED"
            donation.save(update_fields=["status"])
        return render(
            request,
            "donations/error.html",
            {
                "message": (
                    "We were unable to connect to the payment gateway. "
                    "Please try again in a few minutes. "
                    f"Your reference is {donation.reference} — quote it if you contact us."
                )
            },
            status=502,
        )

    return redirect(redirect_url)


@require_http_methods(["GET"])
def donation_return(request: HttpRequest) -> HttpResponse:
    """
    Browser-facing return URL after Paynow redirect.

    Paynow appends ?reference=... to the return URL. We use it to look up the
    donation and verify current status via a poll. This page is COSMETIC — the
    IPN result URL is the authoritative source of truth for payment confirmation.
    """
    reference = request.GET.get("reference", "").strip()

    if not reference:
        # Paynow doesn't always append the reference; fall back to a generic thank-you.
        return render(
            request,
            "donations/thank_you.html",
            {"donation": None, "status": "unknown"},
        )

    try:
        donation = Donation.objects.select_related("donor").get(reference=reference)
    except Donation.DoesNotExist:
        logger.warning("Return URL hit with unknown reference '%s'.", reference)
        return render(
            request,
            "donations/error.html",
            {"message": "We could not find your donation record. Please contact us."},
            status=404,
        )

    # Poll Paynow to get the freshest status; IPN may not have arrived yet.
    paynow_service.verify_payment(donation)
    donation.refresh_from_db()

    return render(
        request,
        "donations/thank_you.html",
        {"donation": donation, "status": donation.status},
    )


@csrf_exempt
@require_http_methods(["POST"])
def paynow_result(request: HttpRequest) -> HttpResponse:
    """
    Paynow IPN endpoint — server-to-server POST, CSRF-exempt.

    This is the SOURCE OF TRUTH for payment confirmation. It may be called
    multiple times by Paynow (retry logic on their side), so the handler is
    fully idempotent:
      - Already-terminal donations are not re-processed.
      - Email is only sent once (guarded by the PENDING→PAID state transition).

    Paynow posts form fields including 'reference' (our reference) and 'status'.
    We look up the donation by our reference, then poll via the stored poll URL
    rather than trusting the POST body directly.
    """
    # Paynow POSTs form-encoded data; 'reference' is our donation reference.
    reference = request.POST.get("reference", "").strip()

    if not reference:
        logger.warning("IPN hit with no 'reference' field in POST body.")
        # Return 200 to prevent Paynow retrying indefinitely for a malformed request.
        return HttpResponse("OK", status=200)

    try:
        donation = Donation.objects.select_related("donor").get(reference=reference)
    except Donation.DoesNotExist:
        logger.error(
            "IPN received for unknown reference '%s'. Possible misconfiguration.", reference
        )
        return HttpResponse("OK", status=200)

    if donation.status in TERMINAL_STATES:
        logger.info(
            "IPN for donation %s ignored — already in terminal state %s.",
            reference,
            donation.status,
        )
        return HttpResponse("OK", status=200)

    # Verify via poll URL (authoritative) rather than trusting POST body.
    paynow_service.verify_payment(donation)

    return HttpResponse("OK", status=200)
