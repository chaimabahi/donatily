from django.conf import settings
from .api_client import APIClient


def portal_context(request):
    user = request.session.get("user")
    unread_notifications = 0

    # Optional: fetch unread notifications count if user is logged in
    if user and request.session.get("access_token"):
        # We can fetch quickly or read from session
        unread_notifications = request.session.get("unread_notifications", 0)

    return {
        "current_user": user,
        "is_authenticated": bool(user),
        "user_role": user.get("role") if user else None,
        "unread_notifications": unread_notifications,
        "backend_api_url": settings.BACKEND_API_URL,
    }
