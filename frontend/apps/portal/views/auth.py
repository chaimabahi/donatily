from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.portal.api_client import APIClient, format_api_errors


def dashboard_router(request):
    """Directs logged-in users to their role dashboard."""
    user = request.session.get("user")
    if not user:
        return redirect("portal-landing")
    role = user.get("role")
    if role == "association":
        return redirect("association-dashboard")
    elif role == "merchant":
        return redirect("merchant-dashboard")
    elif role == "admin":
        return redirect("admin-dashboard")
    return redirect("portal-landing")


def login_view(request):
    """Handles authentication and session creation."""
    if request.session.get("user"):
        return dashboard_router(request)

    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        client = APIClient(request)
        status_code, data = client.post(
            "/api/auth/login/",
            json={"email": email, "password": password},
        )

        if status_code == 200:
            request.session["access_token"] = data.get("access")
            request.session["refresh_token"] = data.get("refresh")
            request.session["user"] = data.get("user")
            request.session.modified = True

            user_role = data.get("user", {}).get("role")
            display_name = data.get("user", {}).get("display_name")
            messages.success(request, f"Ravi de vous revoir, {display_name} !")

            if next_url and not next_url.startswith("//"):
                return redirect(next_url)

            if user_role == "association":
                return redirect("association-dashboard")
            elif user_role == "merchant":
                return redirect("merchant-dashboard")
            elif user_role == "admin":
                return redirect("admin-dashboard")
            return redirect("portal-landing")
        else:
            messages.error(request, format_api_errors(data) or "Identifiants invalides.")

    return render(request, "auth/login.html", {"next": next_url})


def register_association_view(request):
    """Handles Association registration."""
    if request.session.get("user"):
        return dashboard_router(request)

    if request.method == "POST":
        payload = {
            "email": request.POST.get("email", "").strip(),
            "password": request.POST.get("password", ""),
            "password_confirm": request.POST.get("password_confirm", ""),
            "phone": request.POST.get("phone", "").strip(),
            "name": request.POST.get("name", "").strip(),
            "registration_number": request.POST.get("registration_number", "").strip(),
            "city": request.POST.get("city", "").strip(),
            "address": request.POST.get("address", "").strip(),
            "description": request.POST.get("description", "").strip(),
        }

        client = APIClient(request)
        status_code, data = client.post("/api/auth/register/association/", json=payload)

        if status_code == 201:
            request.session["access_token"] = data.get("access")
            request.session["refresh_token"] = data.get("refresh")
            request.session["user"] = data.get("user")
            request.session.modified = True
            messages.success(
                request,
                "Votre compte association a été créé avec succès ! Il sera activé par nos modérateurs sous 24h.",
            )
            return redirect("association-dashboard")
        else:
            messages.error(request, format_api_errors(data))

    return render(request, "auth/register_association.html")


def register_merchant_view(request):
    """Handles Merchant partner registration."""
    if request.session.get("user"):
        return dashboard_router(request)

    if request.method == "POST":
        payload = {
            "email": request.POST.get("email", "").strip(),
            "password": request.POST.get("password", ""),
            "password_confirm": request.POST.get("password_confirm", ""),
            "phone": request.POST.get("phone", "").strip(),
            "business_name": request.POST.get("business_name", "").strip(),
            "tax_id": request.POST.get("tax_id", "").strip(),
            "city": request.POST.get("city", "").strip(),
            "address": request.POST.get("address", "").strip(),
            "description": request.POST.get("description", "").strip(),
            "opening_hours": request.POST.get("opening_hours", "").strip(),
        }

        client = APIClient(request)
        status_code, data = client.post("/api/auth/register/merchant/", json=payload)

        if status_code == 201:
            request.session["access_token"] = data.get("access")
            request.session["refresh_token"] = data.get("refresh")
            request.session["user"] = data.get("user")
            request.session.modified = True
            messages.success(
                request,
                "Bienvenue parmi nos commerçants partenaires ! Votre compte a été créé et est en cours de validation.",
            )
            return redirect("merchant-dashboard")
        else:
            messages.error(request, format_api_errors(data))

    return render(request, "auth/register_merchant.html")


def logout_view(request):
    """Logs out user, revokes token, and flushes session."""
    refresh = request.session.get("refresh_token")
    if refresh:
        client = APIClient(request)
        client.post("/api/auth/logout/", json={"refresh": refresh})

    request.session.flush()
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect("portal-landing")


def notifications_view(request):
    """Shows notifications and marks them as read."""
    client = APIClient(request)
    if request.method == "POST":
        # Mark all as read
        client.post("/api/notifications/read-all/")
        messages.success(request, "Toutes les notifications sont marquées comme lues.")
        return redirect("portal-notifications")

    status_code, data = client.get("/api/notifications/")
    notifications = data.get("results", []) if isinstance(data, dict) else []

    return render(request, "auth/notifications.html", {"notifications": notifications})


def profile_view(request):
    """Account overview and password change."""
    client = APIClient(request)
    user = request.session.get("user")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "change_password":
            old_password = request.POST.get("old_password", "")
            new_password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")

            if new_password != confirm_password:
                messages.error(request, "Les nouveaux mots de passe ne correspondent pas.")
            else:
                code, resp = client.post(
                    "/api/auth/password/",
                    json={"old_password": old_password, "new_password": new_password},
                )
                if code == 200:
                    messages.success(request, "Mot de passe modifié avec succès !")
                else:
                    messages.error(request, format_api_errors(resp))

        elif action == "update_contact":
            phone = request.POST.get("phone", "").strip()
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            code, resp = client.patch(
                "/api/auth/me/",
                json={"phone": phone, "first_name": first_name, "last_name": last_name},
            )
            if code == 200:
                request.session["user"] = resp
                request.session.modified = True
                messages.success(request, "Coordonnées mises à jour avec succès.")
            else:
                messages.error(request, format_api_errors(resp))

        return redirect("portal-profile")

    return render(request, "auth/profile.html", {"user": user})
