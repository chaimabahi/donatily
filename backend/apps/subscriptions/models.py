from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class SubscriptionPlan(models.Model):
    merchant = models.ForeignKey("merchants.Merchant", on_delete=models.CASCADE, related_name="plans")
    name = models.CharField(max_length=160)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    credits = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    duration_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["price", "name"]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="plan_price_gte_0"),
            models.CheckConstraint(condition=models.Q(credits__gte=0), name="plan_credits_gte_0"),
            models.CheckConstraint(condition=models.Q(duration_days__gt=0), name="plan_duration_gt_0"),
        ]

    def __str__(self):
        return f"{self.name} — {self.merchant}"


class Subscription(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        ACTIVE = "active", "Actif"
        REJECTED = "rejected", "Refusé"
        CANCELLED = "cancelled", "Résilié"
        EXPIRED = "expired", "Expiré"

    association = models.ForeignKey("associations.Association", on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "end_date"])]

    def __str__(self):
        return f"{self.association} → {self.plan}"


class CreditTransaction(models.Model):
    class Type(models.TextChoices):
        GRANT = "grant", "Attribution"
        DEBIT = "debit", "Débit"
        REFUND = "refund", "Remboursement"
        ADJUSTMENT = "adjustment", "Ajustement"

    association = models.ForeignKey(
        "associations.Association", on_delete=models.CASCADE, related_name="credit_transactions"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    tx_type = models.CharField(max_length=20, choices=Type.choices)
    description = models.CharField(max_length=255)
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.SET_NULL, related_name="credit_transactions")
    reservation = models.ForeignKey(
        "reservations.Reservation", null=True, blank=True, on_delete=models.SET_NULL, related_name="credit_transactions"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="credit_entries"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tx_type} {self.amount}"
