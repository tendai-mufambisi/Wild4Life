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
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    BlogPost, Donation, Donor,
    UserProfile, ROLE_ADMIN, ROLE_MANAGER, ROLE_WRITER, ROLE_CHOICES,
    SiteSettings, TeamMember, Testimonial, GalleryImage, FAQ,
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

    # Group in Python to avoid CONVERT_TZ — shared MySQL hosting has no timezone tables
    daily_raw = (
        Donation.objects
        .filter(created_at__gte=last_30_start)
        .values("created_at", "status", "amount")
    )
    daily_map = {}
    for _row in daily_raw:
        if _row["created_at"]:
            _d = _row["created_at"].date()
            if _d not in daily_map:
                daily_map[_d] = {"count": 0, "raised": None}
            daily_map[_d]["count"] += 1
            if _row["status"] == "PAID":
                daily_map[_d]["raised"] = (daily_map[_d]["raised"] or 0) + float(_row["amount"] or 0)
    labels_30, series_count, series_raised = [], [], []
    for i in range(30):
        d = (last_30_start + timedelta(days=i)).date()
        row = daily_map.get(d, {})
        labels_30.append(d.strftime("%d %b"))
        series_count.append(row.get("count", 0))
        series_raised.append(float(row.get("raised") or 0))

    _monthly_totals: dict[str, float] = defaultdict(float)
    for _r in Donation.objects.filter(status="PAID", paid_at__isnull=False).values("paid_at", "amount"):
        if _r["paid_at"]:
            _monthly_totals[_r["paid_at"].strftime("%Y-%m")] += float(_r["amount"] or 0)
    monthly_qs = [
        {"month_key": k, "total": v} for k, v in sorted(_monthly_totals.items())
    ][-6:]

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
        "chart_labels_monthly": json.dumps([datetime.strptime(r["month_key"], "%Y-%m").strftime("%b %Y") for r in monthly_qs]),
        "chart_monthly":      json.dumps([r["total"] for r in monthly_qs]),
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
    return redirect("donations:blog_list_dash")


@dashboard_login_required
def blog_delete(request: HttpRequest, post_id) -> HttpResponse:
    profile = _get_profile(request.user)
    post = get_object_or_404(BlogPost, pk=post_id)
    if not profile.is_manager and post.author != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        post.delete()
    return redirect("donations:blog_list_dash")


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
        "role_choices": ROLE_CHOICES, "form_data": defaultdict(str, request.POST.dict()),
        "target_user": None, "target_profile": None,
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
        "form_data": defaultdict(str, request.POST.dict()),
    })


@require_role(ROLE_ADMIN)
def user_delete(request: HttpRequest, user_id: int) -> HttpResponse:
    target_user = get_object_or_404(User, pk=user_id, is_staff=True)
    if request.method == "POST" and target_user != request.user and not target_user.is_superuser:
        target_user.delete()
    return redirect("donations:user_list")


# ── Site Settings (admin only) ────────────────────────────────────────────────

@require_role(ROLE_ADMIN)
def site_settings_edit(request: HttpRequest) -> HttpResponse:
    profile = _get_profile(request.user)
    settings = SiteSettings.get()
    errors = {}
    if request.method == "POST":
        settings.address        = request.POST.get("address", "").strip()
        settings.email          = request.POST.get("email", "").strip()
        settings.phone_primary  = request.POST.get("phone_primary", "").strip()
        settings.phone_secondary = request.POST.get("phone_secondary", "").strip()
        settings.whatsapp       = request.POST.get("whatsapp", "").strip()
        settings.office_hours   = request.POST.get("office_hours", "").strip()
        settings.maps_embed_url = request.POST.get("maps_embed_url", "").strip()
        settings.social_facebook  = request.POST.get("social_facebook", "").strip()
        settings.social_instagram = request.POST.get("social_instagram", "").strip()
        settings.social_linkedin  = request.POST.get("social_linkedin", "").strip()
        settings.pvo_number     = request.POST.get("pvo_number", "").strip()
        settings.trust_deed     = request.POST.get("trust_deed", "").strip()
        settings.cert_caption   = request.POST.get("cert_caption", "").strip()
        settings.cert_description = request.POST.get("cert_description", "").strip()
        settings.stat_years     = request.POST.get("stat_years", "").strip()
        settings.stat_districts = request.POST.get("stat_districts", "").strip()
        settings.stat_score     = request.POST.get("stat_score", "").strip()
        if "cert_image" in request.FILES:
            settings.cert_image = request.FILES["cert_image"]
        elif request.POST.get("clear_cert_image"):
            settings.cert_image = None
        if not errors:
            settings.save()
            return redirect("donations:site_settings")
    return render(request, "dashboard/settings.html", {
        "profile": profile, "settings": settings, "errors": errors,
    })


# ── Team members ──────────────────────────────────────────────────────────────

@require_role(ROLE_ADMIN, ROLE_MANAGER)
def team_list(request: HttpRequest) -> HttpResponse:
    members = TeamMember.objects.all()
    return render(request, "dashboard/team_list.html", {
        "members": members, "profile": _get_profile(request.user),
    })


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def team_create(request: HttpRequest) -> HttpResponse:
    profile = _get_profile(request.user)
    errors = {}
    if request.method == "POST":
        errors, member = _save_team_member(request, None)
        if not errors:
            return redirect("donations:team_list")
    return render(request, "dashboard/team_form.html", {
        "profile": profile, "member": None, "errors": errors,
        "form_data": defaultdict(str, request.POST.dict()), "type_choices": TeamMember.TYPE_CHOICES,
    })


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def team_edit(request: HttpRequest, member_id: int) -> HttpResponse:
    profile = _get_profile(request.user)
    member = get_object_or_404(TeamMember, pk=member_id)
    errors = {}
    if request.method == "POST":
        errors, member = _save_team_member(request, member)
        if not errors:
            return redirect("donations:team_list")
    return render(request, "dashboard/team_form.html", {
        "profile": profile, "member": member, "errors": errors,
        "form_data": defaultdict(str, request.POST.dict()), "type_choices": TeamMember.TYPE_CHOICES,
    })


def _save_team_member(request, member):
    errors = {}
    name = request.POST.get("name", "").strip()
    role = request.POST.get("role", "").strip()
    if not name:
        errors["name"] = "Name is required."
    if not role:
        errors["role"] = "Role is required."
    if errors:
        return errors, member
    if member is None:
        member = TeamMember()
    member.name            = name
    member.role            = role
    member.member_type     = request.POST.get("member_type", TeamMember.STAFF)
    member.bio             = request.POST.get("bio", "").strip()
    member.qualifications  = request.POST.get("qualifications", "").strip()
    member.contact_whatsapp = request.POST.get("contact_whatsapp", "").strip()
    member.contact_phone   = request.POST.get("contact_phone", "").strip()
    member.ordering        = int(request.POST.get("ordering", 0) or 0)
    member.is_active       = request.POST.get("is_active") == "on"
    exp = request.POST.get("experience_years", "").strip()
    member.experience_years = int(exp) if exp.isdigit() else None
    if "photo" in request.FILES:
        member.photo = request.FILES["photo"]
    elif request.POST.get("clear_photo"):
        member.photo = None
    member.save()
    return {}, member


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def team_delete(request: HttpRequest, member_id: int) -> HttpResponse:
    member = get_object_or_404(TeamMember, pk=member_id)
    if request.method == "POST":
        member.delete()
    return redirect("donations:team_list")


# ── Testimonials ──────────────────────────────────────────────────────────────

@require_role(ROLE_ADMIN, ROLE_MANAGER)
def testimonial_list(request: HttpRequest) -> HttpResponse:
    items = Testimonial.objects.all()
    return render(request, "dashboard/testimonials_list.html", {
        "testimonials": items, "profile": _get_profile(request.user),
    })


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def testimonial_create(request: HttpRequest) -> HttpResponse:
    profile = _get_profile(request.user)
    errors = {}
    if request.method == "POST":
        errors, _ = _save_testimonial(request, None)
        if not errors:
            return redirect("donations:testimonial_list")
    return render(request, "dashboard/testimonial_form.html", {
        "profile": profile, "item": None, "errors": errors, "form_data": defaultdict(str, request.POST.dict()),
    })


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def testimonial_edit(request: HttpRequest, item_id: int) -> HttpResponse:
    profile = _get_profile(request.user)
    item = get_object_or_404(Testimonial, pk=item_id)
    errors = {}
    if request.method == "POST":
        errors, item = _save_testimonial(request, item)
        if not errors:
            return redirect("donations:testimonial_list")
    return render(request, "dashboard/testimonial_form.html", {
        "profile": profile, "item": item, "errors": errors, "form_data": defaultdict(str, request.POST.dict()),
    })


def _save_testimonial(request, item):
    errors = {}
    name  = request.POST.get("name", "").strip()
    title = request.POST.get("title", "").strip()
    quote = request.POST.get("quote", "").strip()
    if not name:  errors["name"]  = "Name is required."
    if not title: errors["title"] = "Title/role is required."
    if not quote: errors["quote"] = "Quote text is required."
    if errors:
        return errors, item
    if item is None:
        item = Testimonial()
    item.name     = name
    item.title    = title
    item.location = request.POST.get("location", "").strip()
    item.quote    = quote
    item.rating   = int(request.POST.get("rating", 5) or 5)
    item.ordering = int(request.POST.get("ordering", 0) or 0)
    item.is_active = request.POST.get("is_active") == "on"
    item.save()
    return {}, item


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def testimonial_delete(request: HttpRequest, item_id: int) -> HttpResponse:
    item = get_object_or_404(Testimonial, pk=item_id)
    if request.method == "POST":
        item.delete()
    return redirect("donations:testimonial_list")


# ── Gallery ───────────────────────────────────────────────────────────────────

@require_role(ROLE_ADMIN, ROLE_MANAGER)
def gallery_manage(request: HttpRequest) -> HttpResponse:
    profile = _get_profile(request.user)
    if request.method == "POST":
        files = request.FILES.getlist("images")
        caption = request.POST.get("caption", "").strip()
        for f in files:
            GalleryImage.objects.create(image=f, caption=caption)
        return redirect("donations:gallery_manage")
    images = GalleryImage.objects.all()
    return render(request, "dashboard/gallery_manage.html", {
        "images": images, "profile": profile,
    })


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def gallery_delete(request: HttpRequest, image_id: int) -> HttpResponse:
    image = get_object_or_404(GalleryImage, pk=image_id)
    if request.method == "POST":
        image.delete()
    return redirect("donations:gallery_manage")


# ── FAQs ──────────────────────────────────────────────────────────────────────

@require_role(ROLE_ADMIN, ROLE_MANAGER)
def faq_list(request: HttpRequest) -> HttpResponse:
    faqs = FAQ.objects.all()
    return render(request, "dashboard/faq_list.html", {
        "faqs": faqs, "profile": _get_profile(request.user),
    })


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def faq_create(request: HttpRequest) -> HttpResponse:
    profile = _get_profile(request.user)
    errors = {}
    if request.method == "POST":
        errors, _ = _save_faq(request, None)
        if not errors:
            return redirect("donations:faq_list")
    return render(request, "dashboard/faq_form.html", {
        "profile": profile, "faq": None, "errors": errors, "form_data": defaultdict(str, request.POST.dict()),
    })


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def faq_edit(request: HttpRequest, faq_id: int) -> HttpResponse:
    profile = _get_profile(request.user)
    faq = get_object_or_404(FAQ, pk=faq_id)
    errors = {}
    if request.method == "POST":
        errors, faq = _save_faq(request, faq)
        if not errors:
            return redirect("donations:faq_list")
    return render(request, "dashboard/faq_form.html", {
        "profile": profile, "faq": faq, "errors": errors, "form_data": defaultdict(str, request.POST.dict()),
    })


def _save_faq(request, faq):
    errors = {}
    question = request.POST.get("question", "").strip()
    answer   = request.POST.get("answer", "").strip()
    if not question: errors["question"] = "Question is required."
    if not answer:   errors["answer"]   = "Answer is required."
    if errors:
        return errors, faq
    if faq is None:
        faq = FAQ()
    faq.question  = question
    faq.answer    = answer
    faq.ordering  = int(request.POST.get("ordering", 0) or 0)
    faq.is_active = request.POST.get("is_active") == "on"
    faq.save()
    return {}, faq


@require_role(ROLE_ADMIN, ROLE_MANAGER)
def faq_delete(request: HttpRequest, faq_id: int) -> HttpResponse:
    faq = get_object_or_404(FAQ, pk=faq_id)
    if request.method == "POST":
        faq.delete()
    return redirect("donations:faq_list")


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
