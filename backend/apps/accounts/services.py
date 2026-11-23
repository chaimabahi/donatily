from django.db import transaction
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from .models import ActivityLog, Notification, User


def notify(user, title, body, link=""):
    return Notification.objects.create(recipient=user, title=title, body=body, link=link)


def mark_read(notification):
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
    return notification


def log_activity(actor, action, entity_type, entity_id, message, metadata=None):
    return ActivityLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity_type,
        entity_id="" if entity_id is None else str(entity_id),
        message=message,
        metadata=metadata or {},
    )


def _home_link(user):
    if user.role == User.Role.ASSOCIATION:
        return "/association/"
    if user.role == User.Role.MERCHANT:
        return "/merchant/"
    return "/admin-panel/"


@transaction.atomic
def review_account(*, user_id, actor, action, reason=""):
    user = User.objects.select_for_update().get(pk=user_id)
    if user.role == User.Role.ADMIN:
        raise ValidationError({"detail": "Le compte administrateur ne se modère pas ici."})
    profile = user.association_profile if user.role == User.Role.ASSOCIATION else user.merchant_profile
    reason = (reason or "").strip()
    if action == "approve":
        user.is_active = True
        user.is_verified = True
        profile.status = "approved"
        profile.rejection_reason = ""
        title, body = "Compte approuvé", "Votre compte Donatily est vérifié."
    elif action == "reject":
        if not reason:
            raise ValidationError({"reason": "Indiquez un motif de refus."})
        user.is_verified = False
        profile.status = "rejected"
        profile.rejection_reason = reason
        title, body = "Compte refusé", reason
    elif action == "suspend":
        user.is_active = False
        user.is_verified = False
        profile.status = "suspended"
        profile.rejection_reason = reason
        title, body = "Compte suspendu", reason or "Votre compte a été suspendu."
    elif action == "reactivate":
        user.is_active = True
        user.is_verified = True
        profile.status = "approved"
        profile.rejection_reason = ""
        title, body = "Compte réactivé", "Votre compte est de nouveau actif."
    else:
        raise ValidationError({"action": "Action inconnue."})
    user.save(update_fields=["is_active", "is_verified"])
    profile.save(update_fields=["status", "rejection_reason", "updated_at"])
    notify(user, title, body, _home_link(user))
    log_activity(actor, f"account.{action}", "user", user.pk, f"{user.email} : {action}.")
    return user


def validate_uploaded_image(uploaded):
    if uploaded.size > 5 * 1024 * 1024:
        raise ValidationError("L'image dépasse 5 Mo.")
    content_type = getattr(uploaded, "content_type", "") or ""
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValidationError("Formats acceptés : JPEG, PNG ou WEBP.")
    try:
        uploaded.seek(0)
        image = Image.open(uploaded)
        image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("Le fichier n'est pas une image valide.") from exc
    finally:
        uploaded.seek(0)


def absolute_media(request, file_field):
    if not file_field:
        return None
    try:
        url = file_field.url
    except ValueError:
        return None
    if request is not None and str(url).startswith("/"):
        return request.build_absolute_uri(url)
    return url
