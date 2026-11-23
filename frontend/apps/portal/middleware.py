from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


class PortalAuthMiddleware:
    """Ensures routes are protected according to the authenticated user's role."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.session.get("user")
        request.portal_user = user
        path = request.path

        # Protected paths
        if path.startswith("/association/"):
            if not user:
                messages.warning(request, "Veuillez vous connecter pour accéder à l'espace association.")
                return redirect(f"{reverse('portal-login')}?next={path}")
            if user.get("role") != "association":
                messages.error(request, "Accès réservé aux associations.")
                return redirect("portal-dashboard-router")

        elif path.startswith("/merchant/"):
            if not user:
                messages.warning(request, "Veuillez vous connecter pour accéder à l'espace commerçant.")
                return redirect(f"{reverse('portal-login')}?next={path}")
            if user.get("role") != "merchant":
                messages.error(request, "Accès réservé aux commerçants partenaires.")
                return redirect("portal-dashboard-router")

        elif path.startswith("/admin-portal/"):
            if not user:
                messages.warning(request, "Veuillez vous connecter pour accéder à l'espace administrateur.")
                return redirect(f"{reverse('portal-login')}?next={path}")
            if user.get("role") != "admin":
                messages.error(request, "Accès réservé aux administrateurs.")
                return redirect("portal-dashboard-router")

        response = self.get_response(request)
        return response
