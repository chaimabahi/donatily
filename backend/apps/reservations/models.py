from decimal import Decimal

from django.conf import settings
from django.db import models


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        ACCEPTED = "accepted", "Acceptée"
        REJECTED = "rejected", "Refusée"
        CANCELLED = "cancelled", "Annulée"
        COLLECTED = "collected", "Collectée"

    association = models.ForeignKey("associations.Association", on_delete=models.PROTECT, related_name="reservations")
    merchant = models.ForeignKey("merchants.Merchant", on_delete=models.PROTECT, related_name="reservations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    pickup_date = models.DateField()
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    credits_spent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "pickup_date"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(credits_spent__gte=0), name="reservation_credits_spent_gte_0"),
        ]

    def __str__(self):
        return f"Réservation #{self.pk}"


class ReservationItem(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="reservation_items")
    quantity = models.PositiveIntegerField()
    unit_credit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    product_name = models.CharField(max_length=180)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["reservation", "product"], name="unique_product_per_reservation"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="reservation_item_quantity_gt_0"),
        ]

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"


class Collection(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Planifiée"
        COMPLETED = "completed", "Effectuée"
        MISSED = "missed", "Manquée"
        CANCELLED = "cancelled", "Annulée"

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name="collection")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    scheduled_for = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    organized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="organized_collections"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_for", "-created_at"]

    def __str__(self):
        return f"Collecte #{self.pk}"


class ReservationMessage(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservation_messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message #{self.pk} par {self.sender.email} sur #{self.reservation_id}"

