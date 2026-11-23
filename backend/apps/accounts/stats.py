from datetime import datetime

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin, IsAssociation, IsMerchant
from apps.accounts.serializers import ActivityLogSerializer
from apps.associations.models import Association
from apps.beneficiaries.models import Beneficiary
from apps.distributions.models import Distribution
from apps.merchants.models import Merchant
from apps.products.models import Product
from apps.reservations.models import Collection, Reservation
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import expire_due_subscriptions


def _month_series(queryset, date_field="created_at", months=6):
    today = timezone.localdate().replace(day=1)
    keys = []
    year, month = today.year, today.month
    for _ in range(months):
        keys.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    keys.reverse()
    start_year, start_month = keys[0]
    start = datetime(start_year, start_month, 1, tzinfo=timezone.get_current_timezone())
    grouped = (
        queryset.filter(**{f"{date_field}__gte": start})
        .annotate(bucket=TruncMonth(date_field))
        .values("bucket")
        .annotate(total=Count("id"))
    )
    found = {}
    for row in grouped:
        bucket = row["bucket"]
        if bucket is None:
            continue
        found[(bucket.year, bucket.month)] = row["total"]
    return [{"label": f"{year:04d}-{month:02d}", "total": found.get((year, month), 0)} for year, month in keys]


def _counts(queryset, field="status"):
    return {row[field]: row["total"] for row in queryset.values(field).annotate(total=Count("id"))}


class AssociationStatsView(APIView):
    permission_classes = [IsAssociation]

    def get(self, request):
        expire_due_subscriptions()
        association = request.user.association_profile
        subscription = (
            association.subscriptions.filter(status__in=[Subscription.Status.ACTIVE, Subscription.Status.PENDING])
            .select_related("plan__merchant")
            .order_by("-created_at")
            .first()
        )
        month_start = timezone.localdate().replace(day=1)
        payload = {
            "credit_balance": association.credit_balance,
            "beneficiaries": association.beneficiaries.count(),
            "active_beneficiaries": association.beneficiaries.filter(is_active=True).count(),
            "pending_reservations": association.reservations.filter(status=Reservation.Status.PENDING).count(),
            "collections_scheduled": Collection.objects.filter(
                reservation__association=association, status=Collection.Status.SCHEDULED
            ).count(),
            "distributions_this_month": association.distributions.filter(distributed_on__gte=month_start).count(),
            "reservations_by_status": _counts(association.reservations.all()),
            "monthly_distributions": _month_series(association.distributions.all(), "created_at"),
            "subscription": None
            if subscription is None
            else {
                "id": subscription.id,
                "status": subscription.status,
                "plan": subscription.plan.name,
                "merchant": subscription.plan.merchant.business_name,
                "end_date": subscription.end_date,
                "credits": subscription.plan.credits,
            },
        }
        return Response(payload)


class MerchantStatsView(APIView):
    permission_classes = [IsMerchant]

    def get(self, request):
        merchant = request.user.merchant_profile
        products = merchant.products.all()
        payload = {
            "products": products.count(),
            "published_products": products.filter(status=Product.Status.APPROVED).count(),
            "pending_products": products.filter(status=Product.Status.PENDING).count(),
            "stock_units": products.aggregate(total=Sum("stock"))["total"] or 0,
            "pending_reservations": merchant.reservations.filter(status=Reservation.Status.PENDING).count(),
            "scheduled_collections": Collection.objects.filter(
                reservation__merchant=merchant, status=Collection.Status.SCHEDULED
            ).count(),
            "active_subscriptions": Subscription.objects.filter(
                plan__merchant=merchant, status=Subscription.Status.ACTIVE
            ).count(),
            "pending_subscriptions": Subscription.objects.filter(
                plan__merchant=merchant, status=Subscription.Status.PENDING
            ).count(),
            "reservations_by_status": _counts(merchant.reservations.all()),
            "products_by_kind": _counts(products, "kind"),
            "monthly_reservations": _month_series(merchant.reservations.all()),
        }
        return Response(payload)


class AdminStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from apps.accounts.models import ActivityLog

        pending_accounts = Association.objects.filter(status=Association.Status.PENDING).count() + Merchant.objects.filter(
            status=Merchant.Status.PENDING
        ).count()
        payload = {
            "users": User.objects.count(),
            "associations": Association.objects.count(),
            "merchants": Merchant.objects.count(),
            "pending_accounts": pending_accounts,
            "products": Product.objects.count(),
            "pending_products": Product.objects.filter(status=Product.Status.PENDING).count(),
            "reservations": Reservation.objects.count(),
            "collections": Collection.objects.count(),
            "distributions": Distribution.objects.count(),
            "beneficiaries": Beneficiary.objects.count(),
            "active_subscriptions": Subscription.objects.filter(status=Subscription.Status.ACTIVE).count(),
            "users_by_role": _counts(User.objects.all(), "role"),
            "reservations_by_status": _counts(Reservation.objects.all()),
            "monthly_reservations": _month_series(Reservation.objects.all()),
            "recent_activity": ActivityLogSerializer(
                ActivityLog.objects.select_related("actor")[:8], many=True
            ).data,
        }
        return Response(payload)
