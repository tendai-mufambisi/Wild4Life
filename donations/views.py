"""
Views for Wild4Life donation payment flow and public site pages.

URL map:
  GET      /                    → home (public site)
  GET      /about/              → about page
  GET      /services/           → services page
  GET      /gallery/            → gallery page
  GET      /team/               → team page
  GET      /testimonials/       → testimonials page
  GET      /contact/            → contact page
  POST     /contact/submit/     → contact form handler (AJAX, email)
  GET/POST /donate/             → donation form
  GET      /donation/return/    → Paynow browser return
  POST     /paynow/result/      → Paynow IPN
"""

import logging

from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django.core.paginator import Paginator

from .forms import DonationForm
from .models import BlogPost, Donor, Donation, TERMINAL_STATES
from . import paynow_service

logger = logging.getLogger(__name__)


# ── Public site pages ──────────────────────────────────────────────────────────

def home(request: HttpRequest) -> HttpResponse:
    latest_posts = BlogPost.objects.filter(status="published").order_by("-published_at")[:3]
    return render(request, "site/home.html", {"latest_posts": latest_posts})


def about(request: HttpRequest) -> HttpResponse:
    return render(request, "site/about.html")


def services(request: HttpRequest) -> HttpResponse:
    return render(request, "site/services.html")


def gallery(request: HttpRequest) -> HttpResponse:
    return render(request, "site/gallery.html")


def team(request: HttpRequest) -> HttpResponse:
    return render(request, "site/team.html")


def testimonials(request: HttpRequest) -> HttpResponse:
    return render(request, "site/testimonials.html")


def contact(request: HttpRequest) -> HttpResponse:
    return render(request, "site/contact.html")


def blog_list(request: HttpRequest) -> HttpResponse:
    qs = BlogPost.objects.filter(status="published").select_related("author").order_by("-published_at")
    paginator = Paginator(qs, 9)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "site/blog_list.html", {"page_obj": page, "posts": page.object_list})


def blog_detail(request: HttpRequest, slug: str) -> HttpResponse:
    post = get_object_or_404(BlogPost, slug=slug, status="published")
    related = BlogPost.objects.filter(status="published").exclude(pk=post.pk).order_by("-published_at")[:3]
    return render(request, "site/blog_detail.html", {"post": post, "related": related})


@csrf_exempt
@require_http_methods(["POST"])
def contact_submit(request: HttpRequest) -> HttpResponse:
    """
    AJAX endpoint consumed by the php-email-form validate.js library.
    Returns empty string on success, plain-text error message on failure.
    """
    name    = request.POST.get("name", "").strip()
    email   = request.POST.get("email", "").strip()
    subject = request.POST.get("subject", "").strip()
    message = request.POST.get("message", "").strip()

    if not all([name, email, subject, message]):
        return HttpResponse("Please fill in all required fields.", status=400)

    try:
        send_mail(
            subject=f"[Wild4Life Contact] {subject}",
            message=f"From: {name} <{email}>\n\n{message}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["info@wild4lifezw.org"],
            fail_silently=False,
        )
        return HttpResponse("")
    except Exception as exc:
        logger.error("Contact form email failed: %s", exc)
        return HttpResponse("Failed to send your message. Please try again later.", status=500)


# ── Donation payment flow ──────────────────────────────────────────────────────

@require_http_methods(["GET", "POST"])
def donate(request: HttpRequest) -> HttpResponse:
    """
    GET  — render the donation form.
    POST — validate, create donor + donation, initiate Paynow, redirect.
    """
    if request.method == "GET":
        return render(request, "donations/donate.html", {"form": DonationForm()})

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
        logger.error("Paynow initiation returned None for donation %s.", donation.reference)
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
    """Browser-facing return URL after Paynow redirect."""
    reference = request.GET.get("reference", "").strip()

    if not reference:
        return render(request, "donations/thank_you.html", {"donation": None, "status": "unknown"})

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

    paynow_service.verify_payment(donation)
    donation.refresh_from_db()
    return render(request, "donations/thank_you.html", {"donation": donation, "status": donation.status})


@csrf_exempt
@require_http_methods(["POST"])
def paynow_result(request: HttpRequest) -> HttpResponse:
    """Paynow IPN endpoint — server-to-server POST, CSRF-exempt, idempotent."""
    reference = request.POST.get("reference", "").strip()

    if not reference:
        logger.warning("IPN hit with no 'reference' field in POST body.")
        return HttpResponse("OK", status=200)

    try:
        donation = Donation.objects.select_related("donor").get(reference=reference)
    except Donation.DoesNotExist:
        logger.error("IPN received for unknown reference '%s'.", reference)
        return HttpResponse("OK", status=200)

    if donation.status in TERMINAL_STATES:
        logger.info("IPN for donation %s ignored — already in terminal state %s.", reference, donation.status)
        return HttpResponse("OK", status=200)

    paynow_service.verify_payment(donation)
    return HttpResponse("OK", status=200)
