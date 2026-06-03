import json
from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Donation, Donor

_LOGIN_URL = "/dashboard/login/"


def dashboard_login(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("donations:dashboard_index")

    error = None
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", ""),
            password=request.POST.get("password", ""),
        )
        if user is not None and user.is_staff:
            login(request, user)
            return redirect("donations:dashboard_index")
        error = "Invalid credentials or insufficient permissions."

    return render(request, "dashboard/login.html", {"error": error})


def dashboard_logout(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("donations:dashboard_login")


@login_required(login_url=_LOGIN_URL)
def dashboard_index(request: HttpRequest) -> HttpResponse:
    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)
    last_30_start = now - timedelta(days=29)

    # ── Totals ──────────────────────────────────────────────────────────────────
    total_usd    = Donation.objects.filter(status="PAID", currency="USD").aggregate(t=Sum("amount"))["t"] or 0
    total_zwg    = Donation.objects.filter(status="PAID", currency="ZWG").aggregate(t=Sum("amount"))["t"] or 0
    total_donors = Donor.objects.count()
    total_count  = Donation.objects.count()
    paid_count      = Donation.objects.filter(status="PAID").count()
    pending_count   = Donation.objects.filter(status="PENDING").count()
    failed_count    = Donation.objects.filter(status="FAILED").count()
    cancelled_count = Donation.objects.filter(status="CANCELLED").count()
    success_rate    = round(paid_count / total_count * 100, 1) if total_count else 0
    avg_donation    = Donation.objects.filter(status="PAID").aggregate(a=Avg("amount"))["a"] or 0

    # ── Today / Month ────────────────────────────────────────────────────────────
    today_count  = Donation.objects.filter(created_at__date=today).count()
    today_raised = Donation.objects.filter(status="PAID", paid_at__date=today).aggregate(t=Sum("amount"))["t"] or 0
    month_raised = Donation.objects.filter(status="PAID", paid_at__date__gte=month_start).aggregate(t=Sum("amount"))["t"] or 0
    month_count  = Donation.objects.filter(created_at__date__gte=month_start).count()

    # ── Daily trend (last 30 days) ───────────────────────────────────────────────
    daily_qs = (
        Donation.objects
        .filter(created_at__gte=last_30_start)
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(
            count=Count("id"),
            raised=Sum("amount", filter=Q(status="PAID")),
        )
        .order_by("day")
    )
    daily_map = {row["day"].date(): row for row in daily_qs}
    labels_30, series_count, series_raised = [], [], []
    for i in range(30):
        d = (last_30_start + timedelta(days=i)).date()
        row = daily_map.get(d, {})
        labels_30.append(d.strftime("%d %b"))
        series_count.append(row.get("count", 0))
        series_raised.append(float(row.get("raised") or 0))

    # ── Monthly revenue (last 6 months) ──────────────────────────────────────────
    monthly_qs = list(
        Donation.objects
        .filter(status="PAID", paid_at__isnull=False)
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )[-6:]
    labels_monthly = [r["month"].strftime("%b %Y") for r in monthly_qs]
    series_monthly  = [float(r["total"]) for r in monthly_qs]

    # ── Top donors ───────────────────────────────────────────────────────────────
    top_donors = list(
        Donor.objects
        .annotate(
            total=Sum("donations__amount", filter=Q(donations__status="PAID")),
            count=Count("donations", filter=Q(donations__status="PAID")),
        )
        .filter(total__isnull=False)
        .order_by("-total")[:5]
    )

    ctx = {
        "total_usd": total_usd,
        "total_zwg": total_zwg,
        "total_donors": total_donors,
        "total_count": total_count,
        "paid_count": paid_count,
        "pending_count": pending_count,
        "failed_count": failed_count,
        "cancelled_count": cancelled_count,
        "success_rate": success_rate,
        "avg_donation": avg_donation,
        "today_count": today_count,
        "today_raised": today_raised,
        "month_raised": month_raised,
        "month_count": month_count,
        "recent": list(Donation.objects.select_related("donor").order_by("-created_at")[:10]),
        "top_donors": top_donors,
        # Chart data (JSON-safe)
        "chart_labels_30": json.dumps(labels_30),
        "chart_count": json.dumps(series_count),
        "chart_raised": json.dumps(series_raised),
        "chart_labels_monthly": json.dumps(labels_monthly),
        "chart_monthly": json.dumps(series_monthly),
        "chart_status": json.dumps([paid_count, pending_count, failed_count, cancelled_count]),
    }
    return render(request, "dashboard/index.html", ctx)


@login_required(login_url=_LOGIN_URL)
def dashboard_donors(request: HttpRequest) -> HttpResponse:
    q = request.GET.get("q", "").strip()
    qs = Donor.objects.annotate(
        total=Sum("donations__amount", filter=Q(donations__status="PAID")),
        paid=Count("donations", filter=Q(donations__status="PAID")),
        total_count=Count("donations"),
    ).order_by("-created_at")
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
            | Q(phone__icontains=q) | Q(email__icontains=q)
        )
    return render(request, "dashboard/donors.html", {"donors": qs, "search": q})


@login_required(login_url=_LOGIN_URL)
def dashboard_donations(request: HttpRequest) -> HttpResponse:
    q      = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    qs     = Donation.objects.select_related("donor").order_by("-created_at")
    if q:
        qs = qs.filter(
            Q(reference__icontains=q)
            | Q(donor__first_name__icontains=q)
            | Q(donor__last_name__icontains=q)
            | Q(donor__phone__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    return render(request, "dashboard/donations_list.html", {
        "donations": qs[:200],
        "search": q,
        "status_filter": status,
    })
