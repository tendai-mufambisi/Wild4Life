"""
Data models for the Wild4Life donation system.

Key design decisions:
- All public IDs are UUIDs (never expose sequential PKs to donors).
- Money is DecimalField — never float.
- Phone numbers are stored in +263XXXXXXXXX canonical form.
- Donation references (W4L-YYYY-NNNNNN) are receipt codes only, not credentials.
- Reference generation uses SELECT FOR UPDATE to prevent race conditions under concurrency.
"""

import uuid
import logging
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify

from .utils import normalize_phone

logger = logging.getLogger(__name__)

CURRENCY_CHOICES = [("USD", "USD"), ("ZWG", "ZWG")]

DONATION_STATUS = [
    ("PENDING",   "Pending"),
    ("PAID",      "Paid"),
    ("CANCELLED", "Cancelled"),
    ("FAILED",    "Failed"),
]

# Terminal states — once here a donation must never be overwritten.
TERMINAL_STATES = {"PAID", "CANCELLED", "FAILED"}


class Donor(models.Model):
    """
    Represents a person who has donated (or attempted to donate).

    De-duplication rule — checked in this priority order:
      1. Phone (primary identity key for Zimbabwean donors).
      2. Email (fallback if phone not yet seen).
      3. Create new record.
    """

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100)
    phone      = models.CharField(max_length=20, db_index=True, unique=True)
    email      = models.EmailField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.phone})"

    @classmethod
    def get_or_create_donor(
        cls,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
    ) -> "Donor":
        """
        Find or create a Donor using phone as the primary deduplication key.

        Resolution order:
          1. Look up by normalised phone → return existing (update name if changed).
          2. Look up by email            → return existing (update name + phone).
          3. Create new Donor.

        Phone is normalised before any lookup so "0773123456" and "+263773123456"
        resolve to the same record.
        """
        normalised_phone = normalize_phone(phone)

        # 1 — phone lookup
        try:
            donor = cls.objects.get(phone=normalised_phone)
            return donor
        except cls.DoesNotExist:
            pass

        # 2 — email lookup
        try:
            donor = cls.objects.get(email=email)
            # Absorb new phone onto existing record (donor got a new SIM, etc.)
            donor.phone = normalised_phone
            donor.save(update_fields=["phone"])
            return donor
        except cls.DoesNotExist:
            pass

        # 3 — create
        return cls.objects.create(
            first_name=first_name,
            last_name=last_name,
            phone=normalised_phone,
            email=email,
        )


class ReferenceCounter(models.Model):
    """
    Internal per-year counter used by Donation.generate_reference().

    Never referenced directly from views or admin — use Donation.generate_reference().
    """

    year    = models.IntegerField(unique=True)
    counter = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "donations"


class Donation(models.Model):
    """
    Records a single donation transaction including its Paynow lifecycle.

    Status state machine:
        PENDING → PAID       (confirmed by IPN / poll)
        PENDING → FAILED     (Paynow error or explicit failure)
        PENDING → CANCELLED  (future: manual admin action)

    Terminal states (PAID, FAILED, CANCELLED) are immutable — the IPN handler
    must refuse to overwrite them to guarantee idempotency.
    """

    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor    = models.ForeignKey(
        Donor,
        on_delete=models.PROTECT,
        related_name="donations",
    )
    reference = models.CharField(max_length=30, unique=True, db_index=True)
    amount    = models.DecimalField(max_digits=12, decimal_places=2)
    currency  = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default=settings.DEFAULT_CURRENCY,
    )
    status    = models.CharField(
        max_length=10,
        choices=DONATION_STATUS,
        default="PENDING",
        db_index=True,
    )

    paynow_poll_url   = models.URLField(blank=True, default="")
    paynow_reference  = models.CharField(max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    paid_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reference} — {self.currency} {self.amount} [{self.status}]"

    @staticmethod
    def generate_reference() -> str:
        """
        Generate a human-friendly receipt reference in the form W4L-YYYY-NNNNNN.

        Uses SELECT FOR UPDATE on _ReferenceCounter to guarantee uniqueness even
        under concurrent requests. The transaction must be open when this is called
        (it is called inside Donation.create_for_donor which wraps with @transaction.atomic).
        """
        year = date.today().year
        with transaction.atomic():
            counter_row, _ = ReferenceCounter.objects.select_for_update().get_or_create(
                year=year,
                defaults={"counter": 0},
            )
            counter_row.counter += 1
            counter_row.save(update_fields=["counter"])
            return f"W4L-{year}-{counter_row.counter:06d}"

    @classmethod
    @transaction.atomic
    def create_for_donor(
        cls,
        donor: Donor,
        amount: Decimal,
        currency: str,
    ) -> "Donation":
        """Create a new PENDING donation with an atomically-generated reference."""
        if amount <= Decimal("0"):
            raise ValueError("Donation amount must be greater than zero.")
        reference = cls.generate_reference()
        return cls.objects.create(
            donor=donor,
            reference=reference,
            amount=amount,
            currency=currency,
            status="PENDING",
        )


# ── User roles ─────────────────────────────────────────────────────────────────

User = get_user_model()

ROLE_ADMIN   = "admin"
ROLE_MANAGER = "manager"
ROLE_WRITER  = "writer"

ROLE_CHOICES = [
    (ROLE_ADMIN,   "Admin"),
    (ROLE_MANAGER, "Manager"),
    (ROLE_WRITER,  "Writer"),
]

ROLE_LABELS = {ROLE_ADMIN: "Admin", ROLE_MANAGER: "Manager", ROLE_WRITER: "Writer"}


class UserProfile(models.Model):
    """
    Extends the built-in User with a role for dashboard access control.

    Admin   — full access: analytics, donations, donors, blog, user management.
    Manager — analytics, donations, donors, all blog posts (publish/unpublish).
    Writer  — only their own blog posts (create/edit drafts, cannot publish).
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_WRITER)

    def __str__(self) -> str:
        return f"{self.user.username} [{self.get_role_display()}]"

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN or self.user.is_superuser

    @property
    def is_manager(self) -> bool:
        return self.role in (ROLE_ADMIN, ROLE_MANAGER) or self.user.is_superuser

    @property
    def can_publish(self) -> bool:
        return self.is_manager

    @property
    def can_manage_users(self) -> bool:
        return self.is_admin


@receiver(post_save, sender=User)
def _ensure_profile(sender, instance, created, **kwargs):
    if created and instance.is_staff:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={"role": ROLE_ADMIN if instance.is_superuser else ROLE_WRITER},
        )


# ── Blog ───────────────────────────────────────────────────────────────────────

BLOG_STATUS = [("draft", "Draft"), ("published", "Published")]


class BlogPost(models.Model):
    """
    A blog post authored by a staff user.

    Content is stored as HTML produced by the Quill rich-text editor.
    Thumbnail is an optional uploaded image.
    Slug is auto-generated from the title and guaranteed unique.
    """

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title       = models.CharField(max_length=255)
    slug        = models.SlugField(max_length=255, unique=True, blank=True)
    excerpt     = models.CharField(max_length=350, blank=True, help_text="Short summary shown on listing pages.")
    content     = models.TextField(help_text="HTML from the rich-text editor.")
    thumbnail   = models.ImageField(upload_to="blog/thumbnails/", blank=True, null=True)
    author      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="blog_posts")
    status      = models.CharField(max_length=15, choices=BLOG_STATUS, default="draft", db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} [{self.status}]"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200]
            slug = base
            n = 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        if self.status == "published" and not self.published_at:
            self.published_at = timezone.now()
        elif self.status == "draft":
            self.published_at = None
        super().save(*args, **kwargs)

    @property
    def reading_time(self) -> int:
        words = len(self.content.split())
        return max(1, round(words / 200))
