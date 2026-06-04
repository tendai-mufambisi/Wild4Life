"""
Custom admin dashboard views for Wild4Life.

Access control:
  All dashboard views require is_staff=True.
  Fine-grained access is enforced by the _require_role() helper:
    admin   — full access (analytics, donations, donors, blog, user management)
    manager — analytics, donations, donors, all blog posts (publish/unpublish)
    writer  — only their own blog posts (create/edit drafts)
"""

import json
from datetime import timedelta
from functools import wraps

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    BlogPost, Donation, Donor,
    UserProfile, ROLE_ADMIN, ROLE_MANAGER, ROLE_WRITER, ROLE_CHOICES,
)

User = get_user_model()
_LOGIN_URL = "/dashboard/login/"


# ── Access control helpers ────────────────────────────────────────────────────

def _get_profile(user):
    """Return UserProfile, creating a default admin one for superusers."""
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        if user.is_superuser:
            profile, _ = UserProfile.objects.get_or_create(
                user=user, defaults={"role": ROLE_ADMIN}
            )
            return profile
        return None


def dashboard_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect(_LOGIN_URL)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_role(*roles):
    """Decorator — roles is a subset of ('admin', 'manager', 'writer')."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated or not request.user.is_staff:
                return redirect(_LOGIN_URL)
            if roles and not request.user.is_superuser:
                profile = _get_profile(request.user)
                if profile is None or profile.role not in roles:
                    return HttpResponseForbidden(
                        "<h2>Access denied</h2><p>You do not have permission to perform this action.</p>"
                    )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ── Auth ──────────────────────────────────────────────────────────────────────

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
            _ensure_profile(user)
            return redirect("donations:dashboard_index")
        error = "Invalid credentials or insufficient permissions."
    return render(request, "dashboard/login.html", {"error": error})


def _ensure_profile(user):
    if user.is_staff:
        UserProfile.objects.get_or_create(
            user=user,
            defaults={"role": ROLE_ADMIN if user.is_superuser else ROLE_WRITER},
        )


def dashboard_logout(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("donations:dashboard_login")


# ── Analytics (home) ──────────────────────────────────────────────────────────

@dashboard_login_required
def dashboard_index(request: HttpRequest) -> HttpResponse:
    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)
    last_30_start = now - timedelta(days=29)

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

    today_count  = Donation.objects.filter(created_at__date=today).count()
    today_raised = Donation.objects.filter(status="PAID", paid_at__date=today).aggregate(t=Sum("amount"))["t"] or 0
    month_raised = Donation.objects.filter(status="PAID", paid_at__date__gte=month_start).aggregate(t=Sum("amount"))["t"] or 0
    month_count  = Donation.objects.filter(created_at__date__gte=month_start).count()

    daily_qs = (
        Donation.objects.filter(created_at__gte=last_30_start)
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(count=Count("id"), raised=Sum("amount", filter=Q(status="PAID")))
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

    monthly_qs = list(
        Donation.objects.filter(status="PAID", paid_at__isnull=False)
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )[-6:]

    top_donors = list(
        Donor.objects.annotate(
            total=Sum("donations__amount", filter=Q(donations__status="PAID")),
            count=Count("donations", filter=Q(donations__status="PAID")),
        ).filter(total__isnull=False).order_by("-total")[:5]
    )

    published_posts = BlogPost.objects.filter(status="published").count()
    draft_posts     = BlogPost.objects.filter(status="draft").count()

    profile = _get_profile(request.user)

    ctx = {
        "profile": profile,
        "total_usd": total_usd, "total_zwg": total_zwg,
        "total_donors": total_donors, "total_count": total_count,
        "paid_count": paid_count, "pending_count": pending_count,
        "failed_count": failed_count, "cancelled_count": cancelled_count,
        "success_rate": success_rate, "avg_donation": avg_donation,
        "today_count": today_count, "today_raised": today_raised,
        "month_raised": month_raised, "month_count": month_count,
        "published_posts": published_posts, "draft_posts": draft_posts,
        "recent": list(Donation.objects.select_related("donor").order_by("-created_at")[:10]),
        "top_donors": top_donors,
        "chart_labels_30":    json.dumps(labels_30),
        "chart_count":        json.dumps(series_count),
        "chart_raised":       json.dumps(series_raised),
        "chart_labels_monthly": json.dumps([r["month"].strftime("%b %Y") for r in monthly_qs]),
        "chart_monthly":      json.dumps([float(r["total"]) for r in monthly_qs]),
        "chart_status":       json.dumps([paid_count, pending_count, failed_count, cancelled_count]),
    }
    return render(request, "dashboard/index.html", ctx)


# ── Donations / Donors lists ──────────────────────────────────────────────────

@require_role(ROLE_ADMIN, ROLE_MANAGER)
def dashboard_donors(request: HttpRequest) -> HttpResponse:
    q = request.GET.get("q", "").strip()
    qs = Donor.objects.annotate(
        total=Sum("donations__amount", filter=Q(donations__status="PAID")),
        paid=Count("donations", filter=Q(donations__status="PAID")),
        total_count=Count("donations"),
    ).order_by("-created_at")
    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q)
                       | Q(phone__icontains=q) | Q(email__icontains=q))
    return render(request, "dashboard/donors.html", {
        "donors": qs, "search": q, "profile": _get_profile(request.user),
    })


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def dashboard_donations(request: HttpRequest) -> HttpResponse:
    q      = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    qs     = Donation.objects.select_related("donor").order_by("-created_at")
    if q:
        qs = qs.filter(Q(reference__icontains=q) | Q(donor__first_name__icontains=q)
                       | Q(donor__last_name__icontains=q) | Q(donor__phone__icontains=q))
    if status:
        qs = qs.filter(status=status)
    return render(request, "dashboard/donations_list.html", {
        "donations": qs[:200], "search": q, "status_filter": status,
        "profile": _get_profile(request.user),
    })


# ── Blog management ───────────────────────────────────────────────────────────

@dashboard_login_required
def blog_list(request: HttpRequest) -> HttpResponse:
    profile = _get_profile(request.user)
    if profile and profile.is_manager:
        posts = BlogPost.objects.select_related("author").order_by("-created_at")
    else:
        posts = BlogPost.objects.filter(author=request.user).order_by("-created_at")
    return render(request, "dashboard/blog_list.html", {"posts": posts, "profile": profile})


@dashboard_login_required
def blog_create(request: HttpRequest) -> HttpResponse:
    profile = _get_profile(request.user)
    if request.method == "POST":
        return _save_blog(request, None, profile)
    return render(request, "dashboard/blog_editor.html", {
        "post": None,
        "profile": profile,
        "saved_title": "",
        "saved_excerpt": "",
        "saved_content": "",
    })


@dashboard_login_required
def blog_edit(request: HttpRequest, post_id) -> HttpResponse:
    profile = _get_profile(request.user)
    post = get_object_or_404(BlogPost, pk=post_id)
    if not profile.is_manager and post.author != request.user:
        return HttpResponseForbidden("<h2>Access denied</h2><p>You can only edit your own posts.</p>")
    if request.method == "POST":
        return _save_blog(request, post, profile)
    return render(request, "dashboard/blog_editor.html", {
        "post": post,
        "profile": profile,
        "saved_title": post.title,
        "saved_excerpt": post.excerpt,
        "saved_content": post.content,
    })


def _save_blog(request, post, profile):
    title   = request.POST.get("title", "").strip()
    excerpt = request.POST.get("excerpt", "").strip()
    content = request.POST.get("content", "").strip()
    status  = request.POST.get("status", "draft")

    # Writers can only save drafts
    if profile and not profile.can_publish:
        status = "draft"

    errors = {}
    if not title:
        errors["title"] = "Title is required."
    if not content or content == "<p><br></p>":
        errors["content"] = "Content cannot be empty."

    if errors:
        return render(request, "dashboard/blog_editor.html", {
            "post": post, "profile": profile, "errors": errors,
            "saved_title": title, "saved_excerpt": excerpt, "saved_content": content,
        })

    if post is None:
        post = BlogPost(author=request.user)

    post.title   = title
    post.excerpt = excerpt
    post.content = content
    post.status  = status

    if "thumbnail" in request.FILES:
        post.thumbnail = request.FILES["thumbnail"]
    elif request.POST.get("clear_thumbnail"):
        post.thumbnail = None

    post.save()
    return redirect("donations:blog_list")


@dashboard_login_required
def blog_delete(request: HttpRequest, post_id) -> HttpResponse:
    profile = _get_profile(request.user)
    post = get_object_or_404(BlogPost, pk=post_id)
    if not profile.is_manager and post.author != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        post.delete()
    return redirect("donations:blog_list")


# ── User management (admin only) ──────────────────────────────────────────────

@require_role(ROLE_ADMIN)
def user_list(request: HttpRequest) -> HttpResponse:
    users = (
        User.objects.filter(is_staff=True)
        .prefetch_related("profile")
        .order_by("username")
    )
    return render(request, "dashboard/users.html", {
        "users": users, "profile": _get_profile(request.user),
    })


@require_role(ROLE_ADMIN)
def user_create(request: HttpRequest) -> HttpResponse:
    profile = _get_profile(request.user)
    errors = {}
    if request.method == "POST":
        username  = request.POST.get("username", "").strip()
        email     = request.POST.get("email", "").strip()
        password  = request.POST.get("password", "").strip()
        password2 = request.POST.get("password2", "").strip()
        role      = request.POST.get("role", ROLE_WRITER)
        full_name = request.POST.get("full_name", "").strip()

        if not username:  errors["username"] = "Username is required."
        if User.objects.filter(username=username).exists(): errors["username"] = "Username already taken."
        if not password:  errors["password"] = "Password is required."
        if password != password2: errors["password2"] = "Passwords do not match."
        if role not in dict(ROLE_CHOICES): errors["role"] = "Invalid role."

        if not errors:
            first, _, last = full_name.partition(" ")
            user = User.objects.create_user(
                username=username, email=email, password=password,
                first_name=first, last_name=last, is_staff=True,
            )
            UserProfile.objects.create(user=user, role=role)
            return redirect("donations:user_list")

    return render(request, "dashboard/user_form.html", {
        "action": "Add", "profile": profile, "errors": errors,
        "role_choices": ROLE_CHOICES, "form_data": request.POST,
    })


@require_role(ROLE_ADMIN)
def user_edit(request: HttpRequest, user_id: int) -> HttpResponse:
    profile     = _get_profile(request.user)
    target_user = get_object_or_404(User, pk=user_id, is_staff=True)
    target_profile, _ = UserProfile.objects.get_or_create(
        user=target_user, defaults={"role": ROLE_WRITER}
    )
    errors = {}
    if request.method == "POST":
        role      = request.POST.get("role", ROLE_WRITER)
        email     = request.POST.get("email", "").strip()
        full_name = request.POST.get("full_name", "").strip()
        new_pass  = request.POST.get("password", "").strip()

        if role not in dict(ROLE_CHOICES): errors["role"] = "Invalid role."

        if not errors:
            first, _, last = full_name.partition(" ")
            target_user.email      = email
            target_user.first_name = first
            target_user.last_name  = last
            if new_pass:
                target_user.set_password(new_pass)
            target_user.save()
            target_profile.role = role
            target_profile.save()
            return redirect("donations:user_list")

    return render(request, "dashboard/user_form.html", {
        "action": "Edit", "target_user": target_user, "target_profile": target_profile,
        "profile": profile, "errors": errors, "role_choices": ROLE_CHOICES,
        "form_data": request.POST,
    })


@require_role(ROLE_ADMIN)
def user_delete(request: HttpRequest, user_id: int) -> HttpResponse:
    target_user = get_object_or_404(User, pk=user_id, is_staff=True)
    if request.method == "POST" and target_user != request.user and not target_user.is_superuser:
        target_user.delete()
    return redirect("donations:user_list")


# ── Self-service password change (any dashboard user) ─────────────────────────

@dashboard_login_required
def change_password(request: HttpRequest) -> HttpResponse:
    error = None
    success = False
    if request.method == "POST":
        current   = request.POST.get("current_password", "")
        new_pass  = request.POST.get("new_password", "").strip()
        new_pass2 = request.POST.get("new_password2", "").strip()

        if not request.user.check_password(current):
            error = "Current password is incorrect."
        elif len(new_pass) < 8:
            error = "New password must be at least 8 characters."
        elif new_pass != new_pass2:
            error = "New passwords do not match."
        else:
            request.user.set_password(new_pass)
            request.user.save()
            # Re-authenticate so the session stays alive after password change
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            success = True

    return render(request, "dashboard/change_password.html", {
        "profile": _get_profile(request.user),
        "error": error,
        "success": success,
    })
