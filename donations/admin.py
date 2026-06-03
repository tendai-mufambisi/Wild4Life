"""
Django Admin registrations for the donations app.

Design intent:
- Admin is the sole dashboard — no custom UI built.
- All Paynow fields and timestamps are read-only to prevent hand-editing money records.
- DonationInline on DonorAdmin shows "who donated what and when" per person.
- Per-donor totals are surfaced via a read-only annotation.
"""

from decimal import Decimal

from django.contrib import admin
from django.db.models import Sum, Count, QuerySet
from django.utils.html import format_html

from .models import Donor, Donation


class DonationInline(admin.TabularInline):
    model = Donation
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ("reference", "amount", "currency", "status", "created_at", "paid_at")
    readonly_fields = ("reference", "amount", "currency", "status", "created_at", "paid_at")

    def has_add_permission(self, request, obj=None):  # noqa: ANN001
        return False


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display  = ("__str__", "email", "total_donated", "donation_count", "created_at")
    search_fields = ("first_name", "last_name", "phone", "email")
    readonly_fields = ("id", "created_at", "total_donated", "donation_count")
    inlines = [DonationInline]

    def get_queryset(self, request) -> QuerySet:  # noqa: ANN001
        return (
            super()
            .get_queryset(request)
            .annotate(
                _total=Sum("donations__amount"),
                _count=Count("donations"),
            )
        )

    @admin.display(description="Total donated", ordering="_total")
    def total_donated(self, obj: Donor) -> str:
        total: Decimal = getattr(obj, "_total", None) or Decimal("0")
        return f"USD {total:,.2f}"

    @admin.display(description="# donations", ordering="_count")
    def donation_count(self, obj: Donor) -> int:
        return getattr(obj, "_count", 0)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display   = (
        "reference",
        "donor_name",
        "donor_phone",
        "amount",
        "currency",
        "status",
        "created_at",
        "paid_at",
    )
    search_fields  = (
        "reference",
        "donor__first_name",
        "donor__last_name",
        "donor__phone",
        "donor__email",
    )
    list_filter    = ("status", "currency", "created_at")
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "reference",
        "donor",
        "amount",
        "currency",
        "paynow_poll_url",
        "paynow_reference",
        "created_at",
        "paid_at",
    )
    # Admins may only update status (e.g. manual CANCELLED) — all financial fields locked.
    fields = (
        "id",
        "reference",
        "donor",
        "amount",
        "currency",
        "status",
        "paynow_poll_url",
        "paynow_reference",
        "created_at",
        "paid_at",
    )

    @admin.display(description="Donor", ordering="donor__last_name")
    def donor_name(self, obj: Donation) -> str:
        return str(obj.donor)

    @admin.display(description="Phone", ordering="donor__phone")
    def donor_phone(self, obj: Donation) -> str:
        return obj.donor.phone
