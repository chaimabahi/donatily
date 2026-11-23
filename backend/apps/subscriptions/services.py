from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.services import log_activity, notify
from apps.associations.models import Association

from .models import CreditTransaction, Subscription


def expire_due_subscriptions():
    today = timezone.localdate()
    return Subscription.objects.filter(status=Subscription.Status.ACTIVE, end_date__lt=today).update(
        status=Subscription.Status.EXPIRED
    )


def apply_credit(*, association, amount, tx_type, description, subscription=None, reservation=None, created_by=None):
    amount = Decimal(amount).quantize(Decimal("0.01"))
    locked = Association.objects.select_for_update().get(pk=association.pk)
    balance = (locked.credit_balance + amount).quantize(Decimal("0.01"))
    if balance < 0:
        raise ValidationError({"detail": "Crédits insuffisants."})
    locked.credit_balance = balance
    locked.save(update_fields=["credit_balance", "updated_at"])
    association.credit_balance = balance
    return CreditTransaction.objects.create(
        association=locked,
        amount=amount,
        balance_after=balance,
        tx_type=tx_type,
        description=description[:255],
        subscription=subscription,
        reservation=reservation,
        created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
    )


def _merchant_or_admin(plan_or_sub_merchant_user_id, actor):
    if actor.role == "admin":
        return
    if actor.role != "merchant" or plan_or_sub_merchant_user_id != actor.id:
        raise PermissionDenied("Action réservée au commerçant concerné.")


@transaction.atomic
def request_subscription(*, association, plan, actor):
    if association.status != Association.Status.APPROVED or not association.user.is_verified:
        raise ValidationError({"detail": "Seule une association vérifiée peut s'abonner."})
    if not plan.is_active or plan.merchant.status != "approved":
        raise ValidationError({"plan_id": "Cette formule n'est pas disponible."})
    expire_due_subscriptions()
    if Subscription.objects.filter(
        association=association,
        status__in=[Subscription.Status.PENDING, Subscription.Status.ACTIVE],
    ).exists():
        raise ValidationError({"detail": "Vous avez déjà un abonnement en cours ou en attente."})
    subscription = Subscription.objects.create(association=association, plan=plan)
    notify(
        plan.merchant.user,
        "Demande d'abonnement",
        f"{association.name} souhaite souscrire à « {plan.name} ».",
        f"/merchant/subscriptions/",
    )
    log_activity(actor, "subscription.request", "subscription", subscription.pk, f"Demande d'abonnement #{subscription.pk}.")
    return subscription


@transaction.atomic
def accept_subscription(*, subscription_id, actor):
    subscription = (
        Subscription.objects.select_for_update()
        .select_related("plan__merchant__user", "association__user")
        .get(pk=subscription_id)
    )
    _merchant_or_admin(subscription.plan.merchant.user_id, actor)
    if subscription.status != Subscription.Status.PENDING:
        raise ValidationError({"detail": "Seule une demande en attente peut être acceptée."})
    if Subscription.objects.filter(association=subscription.association, status=Subscription.Status.ACTIVE).exists():
        raise ValidationError({"detail": "Cette association a déjà un abonnement actif."})
    today = timezone.localdate()
    subscription.status = Subscription.Status.ACTIVE
    subscription.start_date = today
    subscription.end_date = today + timedelta(days=subscription.plan.duration_days)
    subscription.rejection_reason = ""
    subscription.save()
    apply_credit(
        association=subscription.association,
        amount=subscription.plan.credits,
        tx_type=CreditTransaction.Type.GRANT,
        description=f"Crédits de la formule {subscription.plan.name}",
        subscription=subscription,
        created_by=actor,
    )
    notify(
        subscription.association.user,
        "Abonnement activé",
        f"Votre formule « {subscription.plan.name} » est active jusqu'au {subscription.end_date:%d/%m/%Y}.",
        "/association/subscriptions/",
    )
    log_activity(actor, "subscription.accept", "subscription", subscription.pk, f"Abonnement #{subscription.pk} activé.")
    return subscription


@transaction.atomic
def reject_subscription(*, subscription_id, actor, reason):
    subscription = (
        Subscription.objects.select_for_update()
        .select_related("plan__merchant__user", "association__user")
        .get(pk=subscription_id)
    )
    _merchant_or_admin(subscription.plan.merchant.user_id, actor)
    if subscription.status != Subscription.Status.PENDING:
        raise ValidationError({"detail": "Seule une demande en attente peut être refusée."})
    if not reason:
        raise ValidationError({"reason": "Indiquez un motif de refus."})
    subscription.status = Subscription.Status.REJECTED
    subscription.rejection_reason = reason
    subscription.save()
    notify(
        subscription.association.user,
        "Abonnement refusé",
        reason,
        "/association/subscriptions/",
    )
    log_activity(actor, "subscription.reject", "subscription", subscription.pk, f"Abonnement #{subscription.pk} refusé.")
    return subscription


@transaction.atomic
def cancel_subscription(*, subscription_id, actor):
    subscription = (
        Subscription.objects.select_for_update()
        .select_related("plan__merchant__user", "association__user", "association")
        .get(pk=subscription_id)
    )
    is_association = actor.role == "association" and subscription.association.user_id == actor.id
    is_merchant = actor.role == "merchant" and subscription.plan.merchant.user_id == actor.id
    if actor.role != "admin" and not is_association and not is_merchant:
        raise PermissionDenied("Vous ne pouvez pas résilier cet abonnement.")
    if subscription.status not in {Subscription.Status.PENDING, Subscription.Status.ACTIVE}:
        raise ValidationError({"detail": "Cet abonnement ne peut plus être résilié."})
    subscription.status = Subscription.Status.CANCELLED
    subscription.save(update_fields=["status", "updated_at"])
    other = subscription.plan.merchant.user if is_association else subscription.association.user
    if actor.role == "admin":
        notify(subscription.association.user, "Abonnement résilié", f"La formule « {subscription.plan.name} » a été résiliée.", "/association/subscriptions/")
        notify(subscription.plan.merchant.user, "Abonnement résilié", f"L'abonnement de {subscription.association.name} a été résilié.", "/merchant/subscriptions/")
    else:
        notify(other, "Abonnement résilié", f"La formule « {subscription.plan.name} » a été résiliée.", "/merchant/subscriptions/" if is_association else "/association/subscriptions/")
    log_activity(actor, "subscription.cancel", "subscription", subscription.pk, f"Abonnement #{subscription.pk} résilié.")
    return subscription
