from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.services import log_activity, notify
from apps.associations.models import Association
from apps.products.models import Product
from apps.subscriptions.models import CreditTransaction
from apps.subscriptions.services import apply_credit

from .models import Collection, Reservation, ReservationItem


def _assert_party(reservation, actor):
    if actor.role == "admin":
        return
    if actor.role == "merchant" and reservation.merchant.user_id == actor.id:
        return
    if actor.role == "association" and reservation.association.user_id == actor.id:
        return
    raise PermissionDenied("Vous n'avez pas accès à cette réservation.")


def _restore_inventory(reservation, actor):
    for item in reservation.items.all():
        product = Product.objects.select_for_update().get(pk=item.product_id)
        product.stock += item.quantity
        product.save(update_fields=["stock", "updated_at"])
    if reservation.credits_spent > 0:
        apply_credit(
            association=reservation.association,
            amount=reservation.credits_spent,
            tx_type=CreditTransaction.Type.REFUND,
            description=f"Remboursement de la réservation #{reservation.pk}",
            reservation=reservation,
            created_by=actor,
        )


@transaction.atomic
def create_reservation(*, association, items, pickup_date, notes, actor):
    if association.status != Association.Status.APPROVED or not association.user.is_verified:
        raise ValidationError({"detail": "Seule une association vérifiée peut réserver."})
    if not items:
        raise ValidationError({"items": "Ajoutez au moins un produit."})
    if pickup_date < timezone.localdate():
        raise ValidationError({"pickup_date": "La date de collecte ne peut pas être passée."})

    merchant = None
    locked_lines = []
    total = Decimal("0.00")
    seen = set()
    for raw in items:
        product_id = raw["product_id"]
        quantity = int(raw["quantity"])
        if product_id in seen:
            raise ValidationError({"items": "Chaque produit ne peut apparaître qu'une fois."})
        seen.add(product_id)
        if quantity < 1:
            raise ValidationError({"items": "La quantité doit être positive."})
        try:
            product = Product.objects.select_for_update().select_related("merchant").get(pk=product_id)
        except Product.DoesNotExist as exc:
            raise ValidationError({"items": "Un des produits est introuvable."}) from exc
        if product.status != Product.Status.APPROVED or product.merchant.status != "approved":
            raise ValidationError({"items": f"{product.name} n'est pas disponible."})
        if merchant is None:
            merchant = product.merchant
        elif product.merchant_id != merchant.id:
            raise ValidationError({"items": "Une réservation concerne un seul commerçant."})
        if quantity > product.stock:
            raise ValidationError({"items": f"Stock insuffisant pour {product.name} ({product.stock} disponible)."})
        unit_cost = Decimal(product.credit_cost).quantize(Decimal("0.01"))
        total += (unit_cost * quantity).quantize(Decimal("0.01"))
        locked_lines.append((product, quantity, unit_cost))

    locked_association = Association.objects.select_for_update().get(pk=association.pk)
    if locked_association.credit_balance < total:
        raise ValidationError({"detail": "Crédits insuffisants pour cette réservation."})

    reservation = Reservation.objects.create(
        association=locked_association,
        merchant=merchant,
        pickup_date=pickup_date,
        notes=(notes or "").strip(),
        credits_spent=total.quantize(Decimal("0.01")),
    )
    for product, quantity, unit_cost in locked_lines:
        product.stock -= quantity
        product.save(update_fields=["stock", "updated_at"])
        ReservationItem.objects.create(
            reservation=reservation,
            product=product,
            quantity=quantity,
            unit_credit_cost=unit_cost,
            product_name=product.name,
        )
    if reservation.credits_spent > 0:
        apply_credit(
            association=locked_association,
            amount=-reservation.credits_spent,
            tx_type=CreditTransaction.Type.DEBIT,
            description=f"Réservation #{reservation.pk} chez {merchant.business_name}",
            reservation=reservation,
            created_by=actor,
        )
    notify(
        merchant.user,
        "Nouvelle réservation",
        f"{locked_association.name} a réservé des produits pour le {pickup_date:%d/%m/%Y}.",
        f"/merchant/reservations/{reservation.pk}/",
    )
    log_activity(
        actor,
        "reservation.create",
        "reservation",
        reservation.pk,
        f"Réservation #{reservation.pk} créée.",
        {"credits": str(reservation.credits_spent)},
    )
    return reservation


@transaction.atomic
def accept_reservation(*, reservation_id, actor, notes=""):
    reservation = Reservation.objects.select_for_update().select_related("association__user", "merchant__user").get(pk=reservation_id)
    if actor.role not in {"merchant", "admin"}:
        raise PermissionDenied("Seuls le commerçant et l'administrateur peuvent accepter une réservation.")
    _assert_party(reservation, actor)
    if reservation.status != Reservation.Status.PENDING:
        raise ValidationError({"detail": "Seule une réservation en attente peut être acceptée."})
    reservation.status = Reservation.Status.ACCEPTED
    reservation.save(update_fields=["status", "updated_at"])
    Collection.objects.create(
        reservation=reservation,
        scheduled_for=reservation.pickup_date,
        notes=(notes or "").strip(),
        organized_by=actor,
    )
    notify(
        reservation.association.user,
        "Réservation acceptée",
        f"{reservation.merchant.business_name} a accepté la collecte du {reservation.pickup_date:%d/%m/%Y}.",
        f"/association/reservations/{reservation.pk}/",
    )
    log_activity(actor, "reservation.accept", "reservation", reservation.pk, f"Réservation #{reservation.pk} acceptée.")
    return reservation


@transaction.atomic
def reject_reservation(*, reservation_id, actor, reason):
    reservation = Reservation.objects.select_for_update().select_related("association", "association__user", "merchant__user").get(pk=reservation_id)
    if actor.role not in {"merchant", "admin"}:
        raise PermissionDenied("Seuls le commerçant et l'administrateur peuvent refuser une réservation.")
    _assert_party(reservation, actor)
    if reservation.status != Reservation.Status.PENDING:
        raise ValidationError({"detail": "Seule une réservation en attente peut être refusée."})
    if not (reason or "").strip():
        raise ValidationError({"reason": "Indiquez un motif de refus."})
    _restore_inventory(reservation, actor)
    reservation.status = Reservation.Status.REJECTED
    reservation.rejection_reason = reason.strip()
    reservation.save(update_fields=["status", "rejection_reason", "updated_at"])
    notify(
        reservation.association.user,
        "Réservation refusée",
        reason.strip(),
        f"/association/reservations/{reservation.pk}/",
    )
    log_activity(actor, "reservation.reject", "reservation", reservation.pk, f"Réservation #{reservation.pk} refusée.")
    return reservation


@transaction.atomic
def cancel_reservation(*, reservation_id, actor, reason=""):
    reservation = Reservation.objects.select_for_update().select_related("association__user", "merchant__user", "association").get(pk=reservation_id)
    _assert_party(reservation, actor)
    if actor.role == "merchant":
        raise PermissionDenied("Le commerçant refuse ou clôture la collecte, il n'annule pas à la place de l'association.")
    if reservation.status not in {Reservation.Status.PENDING, Reservation.Status.ACCEPTED}:
        raise ValidationError({"detail": "Cette réservation ne peut plus être annulée."})
    collection = Collection.objects.select_for_update().filter(reservation=reservation).first()
    if collection and collection.status == Collection.Status.COMPLETED:
        raise ValidationError({"detail": "Une collecte déjà effectuée ne peut pas être annulée."})
    _restore_inventory(reservation, actor)
    if collection and collection.status == Collection.Status.SCHEDULED:
        collection.status = Collection.Status.CANCELLED
        collection.notes = (reason or collection.notes).strip()
        collection.save(update_fields=["status", "notes", "updated_at"])
    reservation.status = Reservation.Status.CANCELLED
    reservation.rejection_reason = (reason or "").strip()
    reservation.save(update_fields=["status", "rejection_reason", "updated_at"])
    notify(
        reservation.merchant.user,
        "Réservation annulée",
        f"{reservation.association.name} a annulé la réservation #{reservation.pk}.",
        f"/merchant/reservations/{reservation.pk}/",
    )
    log_activity(actor, "reservation.cancel", "reservation", reservation.pk, f"Réservation #{reservation.pk} annulée.")
    return reservation


@transaction.atomic
def complete_collection(*, collection_id, actor, notes=""):
    collection = Collection.objects.select_for_update().select_related("reservation__merchant__user", "reservation__association__user").get(pk=collection_id)
    reservation = collection.reservation
    if actor.role not in {"merchant", "admin"}:
        raise PermissionDenied("Seuls le commerçant et l'administrateur peuvent confirmer une collecte.")
    _assert_party(reservation, actor)
    if collection.status != Collection.Status.SCHEDULED or reservation.status != Reservation.Status.ACCEPTED:
        raise ValidationError({"detail": "Cette collecte n'est pas planifiée."})
    collection.status = Collection.Status.COMPLETED
    collection.completed_at = timezone.now()
    if notes:
        collection.notes = notes.strip()
    collection.save()
    reservation.status = Reservation.Status.COLLECTED
    reservation.save(update_fields=["status", "updated_at"])
    notify(
        reservation.association.user,
        "Collecte confirmée",
        f"La collecte chez {reservation.merchant.business_name} est enregistrée.",
        f"/association/collections/",
    )
    log_activity(actor, "collection.complete", "collection", collection.pk, f"Collecte #{collection.pk} effectuée.")
    return collection


@transaction.atomic
def miss_collection(*, collection_id, actor, notes=""):
    collection = Collection.objects.select_for_update().select_related("reservation__association", "reservation__merchant__user", "reservation__association__user").get(pk=collection_id)
    reservation = collection.reservation
    if actor.role not in {"merchant", "admin"}:
        raise PermissionDenied("Seuls le commerçant et l'administrateur peuvent signaler une collecte manquée.")
    _assert_party(reservation, actor)
    if collection.status != Collection.Status.SCHEDULED or reservation.status != Reservation.Status.ACCEPTED:
        raise ValidationError({"detail": "Cette collecte ne peut pas être marquée comme manquée."})
    _restore_inventory(reservation, actor)
    collection.status = Collection.Status.MISSED
    collection.notes = (notes or "Collecte manquée.").strip()
    collection.save(update_fields=["status", "notes", "updated_at"])
    reservation.status = Reservation.Status.CANCELLED
    reservation.rejection_reason = collection.notes
    reservation.save(update_fields=["status", "rejection_reason", "updated_at"])
    notify(
        reservation.association.user,
        "Collecte manquée",
        collection.notes,
        f"/association/reservations/{reservation.pk}/",
    )
    log_activity(actor, "collection.miss", "collection", collection.pk, f"Collecte #{collection.pk} manquée.")
    return collection
