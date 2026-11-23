from django.contrib import messages
from django.shortcuts import redirect, render
from apps.portal.api_client import APIClient, format_api_errors


def dashboard_view(request):
    """Association Dashboard: KPIs, recent reservations, quick actions."""
    client = APIClient(request)

    _, stats = client.get("/api/stats/association/")
    if not isinstance(stats, dict):
        stats = {}

    _, reservations_data = client.get("/api/reservations/", params={"page_size": 5})
    recent_reservations = reservations_data.get("results", []) if isinstance(reservations_data, dict) else []

    _, collections_data = client.get("/api/collections/", params={"status": "scheduled", "page_size": 4})
    upcoming_collections = collections_data.get("results", []) if isinstance(collections_data, dict) else []

    context = {
        "stats": stats,
        "recent_reservations": recent_reservations,
        "upcoming_collections": upcoming_collections,
    }
    return render(request, "association/dashboard.html", context)


def products_catalog_view(request):
    """Browse solidarity donations and discounted products."""
    client = APIClient(request)

    params = {}
    for key in ["category", "kind", "city", "merchant", "q", "page"]:
        val = request.GET.get(key)
        if val:
            params[key] = val

    _, categories_data = client.get("/api/categories/")
    categories = categories_data if isinstance(categories_data, list) else []

    _, merchants_data = client.get("/api/merchants/")
    merchants = merchants_data.get("results", []) if isinstance(merchants_data, dict) else []

    _, products_data = client.get("/api/products/", params=params)
    products = products_data.get("results", []) if isinstance(products_data, dict) else []
    count = products_data.get("count", len(products)) if isinstance(products_data, dict) else len(products)

    context = {
        "categories": categories,
        "merchants": merchants,
        "products": products,
        "total_count": count,
        "selected_category": request.GET.get("category", ""),
        "selected_kind": request.GET.get("kind", ""),
        "selected_city": request.GET.get("city", ""),
        "selected_merchant": request.GET.get("merchant", ""),
        "search_query": request.GET.get("q", ""),
    }
    return render(request, "association/products.html", context)


def product_detail_view(request, pk):
    """View product detail with reservation form."""
    client = APIClient(request)

    code, product = client.get(f"/api/products/{pk}/")
    if code != 200:
        messages.error(request, "Produit introuvable ou indisponible.")
        return redirect("association-products")

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        pickup_date = request.POST.get("pickup_date")
        notes = request.POST.get("notes", "").strip()

        payload = {
            "pickup_date": pickup_date,
            "notes": notes,
            "items": [{"product_id": pk, "quantity": quantity}],
        }

        res_code, res_data = client.post("/api/reservations/", json=payload)
        if res_code == 201:
            messages.success(request, "Votre demande de réservation a été envoyée au commerçant !")
            return redirect("association-reservations")
        else:
            messages.error(request, format_api_errors(res_data))

    return render(request, "association/product_detail.html", {"product": product})


def reservations_view(request):
    """Track reservations and their statuses."""
    client = APIClient(request)

    params = {}
    status_param = request.GET.get("status")
    if status_param:
        params["status"] = status_param

    _, data = client.get("/api/reservations/", params=params)
    reservations = data.get("results", []) if isinstance(data, dict) else []

    context = {
        "reservations": reservations,
        "selected_status": status_param or "",
    }
    return render(request, "association/reservations.html", context)


def reservation_cancel_view(request, pk):
    """Cancel a pending or accepted reservation."""
    client = APIClient(request)
    reason = request.POST.get("reason", "Annulation demandée par l'association.")

    code, resp = client.post(
        f"/api/reservations/{pk}/action/",
        json={"action": "cancel", "reason": reason},
    )
    if code == 200:
        messages.success(request, "Réservation annulée.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("association-reservations")


def reservation_message_send_view(request, pk):
    """Send a message to the merchant for an accepted reservation."""
    if request.method != "POST":
        return redirect("association-reservations")

    client = APIClient(request)
    content = request.POST.get("content", "").strip()
    if not content:
        messages.error(request, "Le message ne peut pas être vide.")
        return redirect("association-reservations")

    code, resp = client.post(
        f"/api/reservations/{pk}/messages/",
        json={"content": content},
    )
    if code == 201:
        messages.success(request, "Votre message a été envoyé au commerçant.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("association-reservations")


def collections_view(request):
    """Track scheduled and completed collections."""
    client = APIClient(request)

    params = {}
    status_param = request.GET.get("status")
    if status_param:
        params["status"] = status_param

    _, data = client.get("/api/collections/", params=params)
    collections = data.get("results", []) if isinstance(data, dict) else []

    context = {
        "collections": collections,
        "selected_status": status_param or "",
    }
    return render(request, "association/collections.html", context)


def plans_view(request):
    """Browse merchant solidarity subscription plans."""
    client = APIClient(request)

    params = {}
    q = request.GET.get("q")
    if q:
        params["q"] = q

    _, data = client.get("/api/plans/", params=params)
    plans = data.get("results", []) if isinstance(data, dict) else []

    return render(request, "association/plans.html", {"plans": plans, "search_query": q or ""})


def subscribe_action_view(request, plan_id):
    """Subscribe to a merchant solidarity plan."""
    client = APIClient(request)

    code, resp = client.post("/api/subscriptions/", json={"plan_id": plan_id})
    if code == 201:
        messages.success(
            request,
            "Demande d'abonnement envoyée au commerçant ! Dès validation, vos crédits seront alloués.",
        )
        return redirect("association-subscriptions")
    else:
        messages.error(request, format_api_errors(resp))
        return redirect("association-plans")


def subscriptions_view(request):
    """Track subscriptions and status."""
    client = APIClient(request)

    _, data = client.get("/api/subscriptions/")
    subscriptions = data.get("results", []) if isinstance(data, dict) else []

    return render(request, "association/subscriptions.html", {"subscriptions": subscriptions})


def subscription_cancel_view(request, pk):
    """Cancel an active or pending subscription."""
    client = APIClient(request)

    code, resp = client.post(f"/api/subscriptions/{pk}/action/", json={"action": "cancel"})
    if code == 200:
        messages.success(request, "Abonnement résilié.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("association-subscriptions")


def credits_view(request):
    """Credits are no longer used; redirect to association dashboard."""
    return redirect("association-dashboard")


def beneficiaries_view(request):
    """Manage beneficiaries and their needs."""
    client = APIClient(request)

    params = {}
    for key in ["priority", "active", "city", "q"]:
        val = request.GET.get(key)
        if val:
            params[key] = val

    _, data = client.get("/api/beneficiaries/", params=params)
    beneficiaries = data.get("results", []) if isinstance(data, dict) else []

    context = {
        "beneficiaries": beneficiaries,
        "selected_priority": request.GET.get("priority", ""),
        "selected_active": request.GET.get("active", ""),
        "search_query": request.GET.get("q", ""),
    }
    return render(request, "association/beneficiaries.html", context)


def beneficiary_create_view(request):
    """Register a new beneficiary."""
    client = APIClient(request)

    if request.method == "POST":
        payload = {
            "first_name": request.POST.get("first_name", "").strip(),
            "last_name": request.POST.get("last_name", "").strip(),
            "phone": request.POST.get("phone", "").strip(),
            "address": request.POST.get("address", "").strip(),
            "city": request.POST.get("city", "").strip(),
            "household_size": int(request.POST.get("household_size", 1)),
            "needs": request.POST.get("needs", "").strip(),
            "priority": request.POST.get("priority", "medium"),
            "notes": request.POST.get("notes", "").strip(),
            "is_active": request.POST.get("is_active") == "on",
        }

        code, resp = client.post("/api/beneficiaries/", json=payload)
        if code == 201:
            messages.success(request, f"Bénéficiaire {payload['first_name']} {payload['last_name']} ajouté.")
            return redirect("association-beneficiaries")
        else:
            messages.error(request, format_api_errors(resp))

    return render(request, "association/beneficiary_form.html", {"mode": "create"})


def beneficiary_edit_view(request, pk):
    """Edit beneficiary."""
    client = APIClient(request)

    code, beneficiary = client.get(f"/api/beneficiaries/{pk}/")
    if code != 200:
        messages.error(request, "Bénéficiaire introuvable.")
        return redirect("association-beneficiaries")

    if request.method == "POST":
        payload = {
            "first_name": request.POST.get("first_name", "").strip(),
            "last_name": request.POST.get("last_name", "").strip(),
            "phone": request.POST.get("phone", "").strip(),
            "address": request.POST.get("address", "").strip(),
            "city": request.POST.get("city", "").strip(),
            "household_size": int(request.POST.get("household_size", 1)),
            "needs": request.POST.get("needs", "").strip(),
            "priority": request.POST.get("priority", "medium"),
            "notes": request.POST.get("notes", "").strip(),
            "is_active": request.POST.get("is_active") == "on",
        }

        up_code, up_resp = client.patch(f"/api/beneficiaries/{pk}/", json=payload)
        if up_code == 200:
            messages.success(request, "Fiche bénéficiaire mise à jour.")
            return redirect("association-beneficiaries")
        else:
            messages.error(request, format_api_errors(up_resp))

    return render(request, "association/beneficiary_form.html", {"mode": "edit", "beneficiary": beneficiary})


def beneficiary_delete_view(request, pk):
    """Delete a beneficiary."""
    client = APIClient(request)
    code, _ = client.delete(f"/api/beneficiaries/{pk}/")
    if code == 204:
        messages.success(request, "Bénéficiaire supprimé.")
    else:
        messages.error(request, "Impossible de supprimer ce bénéficiaire.")
    return redirect("association-beneficiaries")


def distributions_view(request):
    """Track product distributions to beneficiaries."""
    client = APIClient(request)

    params = {}
    for key in ["beneficiary", "date_from", "date_to", "q"]:
        val = request.GET.get(key)
        if val:
            params[key] = val

    _, data = client.get("/api/distributions/", params=params)
    distributions = data.get("results", []) if isinstance(data, dict) else []

    _, ben_data = client.get("/api/beneficiaries/")
    beneficiaries = ben_data.get("results", []) if isinstance(ben_data, dict) else []

    context = {
        "distributions": distributions,
        "beneficiaries": beneficiaries,
        "search_query": request.GET.get("q", ""),
    }
    return render(request, "association/distributions.html", context)


def distribution_create_view(request):
    """Record a distribution."""
    client = APIClient(request)

    _, ben_data = client.get("/api/beneficiaries/", params={"active": "true"})
    beneficiaries = ben_data.get("results", []) if isinstance(ben_data, dict) else []

    if request.method == "POST":
        payload = {
            "beneficiary": request.POST.get("beneficiary"),
            "title": request.POST.get("title", "").strip(),
            "quantity": int(request.POST.get("quantity", 1)),
            "unit": request.POST.get("unit", "piece"),
            "distributed_on": request.POST.get("distributed_on"),
            "notes": request.POST.get("notes", "").strip(),
        }

        code, resp = client.post("/api/distributions/", json=payload)
        if code == 201:
            messages.success(request, "Distribution enregistrée avec succès !")
            return redirect("association-distributions")
        else:
            messages.error(request, format_api_errors(resp))

    return render(
        request,
        "association/distribution_form.html",
        {"beneficiaries": beneficiaries},
    )


def profile_view(request):
    """Association organization profile settings."""
    client = APIClient(request)

    _, assoc = client.get("/api/associations/me/")

    if request.method == "POST":
        data = {
            "name": request.POST.get("name", "").strip(),
            "registration_number": request.POST.get("registration_number", "").strip(),
            "city": request.POST.get("city", "").strip(),
            "address": request.POST.get("address", "").strip(),
            "postal_code": request.POST.get("postal_code", "").strip(),
            "website": request.POST.get("website", "").strip(),
            "description": request.POST.get("description", "").strip(),
        }
        files = {}
        if request.FILES.get("logo"):
            files["logo"] = request.FILES["logo"]

        code, resp = client.patch("/api/associations/me/", data=data, files=files)
        if code == 200:
            messages.success(request, "Profil association mis à jour.")
            return redirect("association-profile")
        else:
            messages.error(request, format_api_errors(resp))

    return render(request, "association/profile.html", {"association": assoc})
