from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect, render
from apps.portal.api_client import APIClient, format_api_errors


def dashboard_view(request):
    """Merchant Dashboard: KPIs, stock status, pending reservations, subscriptions."""
    client = APIClient(request)

    _, stats = client.get("/api/stats/merchant/")
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
    return render(request, "merchant/dashboard.html", context)


def products_view(request):
    """Manage products, donations, unsold goods and discounts."""
    client = APIClient(request)

    params = {"mine": "true"}
    status_param = request.GET.get("status")
    if status_param:
        params["status"] = status_param
    kind_param = request.GET.get("kind")
    if kind_param:
        params["kind"] = kind_param
    q = request.GET.get("q")
    if q:
        params["q"] = q

    _, data = client.get("/api/products/", params=params)
    products = data.get("results", []) if isinstance(data, dict) else []

    _, cat_data = client.get("/api/categories/")
    categories = cat_data if isinstance(cat_data, list) else []

    context = {
        "products": products,
        "categories": categories,
        "selected_status": status_param or "",
        "selected_kind": kind_param or "",
        "search_query": q or "",
    }
    return render(request, "merchant/products.html", context)


def product_create_view(request):
    """Create a new donation, unsold or discounted offer."""
    client = APIClient(request)

    _, cat_data = client.get("/api/categories/")
    categories = cat_data if isinstance(cat_data, list) else []

    if request.method == "POST":
        payload = {
            "name": request.POST.get("name", "").strip(),
            "category": int(request.POST.get("category")),
            "description": request.POST.get("description", "").strip(),
            "kind": request.POST.get("kind"),
            "unit": request.POST.get("unit", "piece"),
            "original_price": request.POST.get("original_price", "0.00"),
            "offer_price": request.POST.get("offer_price", "0.00"),
            "credit_cost": request.POST.get("credit_cost", "0.00"),
            "stock": int(request.POST.get("stock", 0)),
            "expiry_date": request.POST.get("expiry_date") or None,
        }

        code, resp = client.post("/api/products/", json=payload)
        if code == 201:
            product_id = resp["id"]
            # Handle image if provided
            if request.FILES.get("image"):
                client.post(
                    f"/api/products/{product_id}/images/",
                    files={"image": request.FILES["image"]},
                    data={"is_primary": "True", "alt_text": payload["name"]},
                )
            messages.success(request, f"Produit « {payload['name']} » soumis pour modération !")
            return redirect("merchant-products")
        else:
            messages.error(request, format_api_errors(resp))

    return render(request, "merchant/product_form.html", {"mode": "create", "categories": categories})


def product_edit_view(request, pk):
    """Edit existing product."""
    client = APIClient(request)

    code, product = client.get(f"/api/products/{pk}/")
    if code != 200:
        messages.error(request, "Produit introuvable.")
        return redirect("merchant-products")

    _, cat_data = client.get("/api/categories/")
    categories = cat_data if isinstance(cat_data, list) else []

    if request.method == "POST":
        payload = {
            "name": request.POST.get("name", "").strip(),
            "category": int(request.POST.get("category")),
            "description": request.POST.get("description", "").strip(),
            "kind": request.POST.get("kind"),
            "unit": request.POST.get("unit", "piece"),
            "original_price": request.POST.get("original_price", "0.00"),
            "offer_price": request.POST.get("offer_price", "0.00"),
            "credit_cost": request.POST.get("credit_cost", "0.00"),
            "stock": int(request.POST.get("stock", 0)),
            "expiry_date": request.POST.get("expiry_date") or None,
        }

        up_code, up_resp = client.patch(f"/api/products/{pk}/", json=payload)
        if up_code == 200:
            if request.FILES.get("image"):
                client.post(
                    f"/api/products/{pk}/images/",
                    files={"image": request.FILES["image"]},
                    data={"is_primary": "True", "alt_text": payload["name"]},
                )
            messages.success(request, f"Produit « {payload['name']} » mis à jour.")
            return redirect("merchant-products")
        else:
            messages.error(request, format_api_errors(up_resp))

    return render(
        request,
        "merchant/product_form.html",
        {"mode": "edit", "product": product, "categories": categories},
    )


def product_delete_view(request, pk):
    """Delete a product."""
    client = APIClient(request)
    code, _ = client.delete(f"/api/products/{pk}/")
    if code == 204:
        messages.success(request, "Produit supprimé du catalogue.")
    else:
        messages.error(request, "Impossible de supprimer ce produit.")
    return redirect("merchant-products")


def plans_view(request):
    """Manage merchant's solidarity subscription plans."""
    client = APIClient(request)

    _, data = client.get("/api/plans/", params={"mine": "true"})
    plans = data.get("results", []) if isinstance(data, dict) else []

    return render(request, "merchant/plans.html", {"plans": plans})


def plan_create_view(request):
    """Create a new solidarity subscription plan."""
    client = APIClient(request)

    if request.method == "POST":
        payload = {
            "name": request.POST.get("name", "").strip(),
            "description": request.POST.get("description", "").strip(),
            "price": request.POST.get("price", "0.00"),
            "credits": request.POST.get("credits", "10.00"),
            "duration_days": int(request.POST.get("duration_days", 30)),
            "is_active": request.POST.get("is_active") == "on",
        }

        code, resp = client.post("/api/plans/", json=payload)
        if code == 201:
            messages.success(request, f"Formule « {payload['name']} » créée avec succès !")
            return redirect("merchant-plans")
        else:
            messages.error(request, format_api_errors(resp))

    return render(request, "merchant/plan_form.html", {"mode": "create"})


def plan_edit_view(request, pk):
    """Edit or deactivate plan."""
    client = APIClient(request)

    code, plan = client.get(f"/api/plans/{pk}/")
    if code != 200:
        messages.error(request, "Formule introuvable.")
        return redirect("merchant-plans")

    if request.method == "POST":
        payload = {
            "name": request.POST.get("name", "").strip(),
            "description": request.POST.get("description", "").strip(),
            "price": request.POST.get("price", "0.00"),
            "credits": request.POST.get("credits", "10.00"),
            "duration_days": int(request.POST.get("duration_days", 30)),
            "is_active": request.POST.get("is_active") == "on",
        }

        up_code, up_resp = client.patch(f"/api/plans/{pk}/", json=payload)
        if up_code == 200:
            messages.success(request, "Formule mise à jour.")
            return redirect("merchant-plans")
        else:
            messages.error(request, format_api_errors(up_resp))

    return render(request, "merchant/plan_form.html", {"mode": "edit", "plan": plan})


def subscriptions_view(request):
    """Manage association subscriptions to the merchant's plans."""
    client = APIClient(request)

    _, data = client.get("/api/subscriptions/")
    subscriptions = data.get("results", []) if isinstance(data, dict) else []

    return render(request, "merchant/subscriptions.html", {"subscriptions": subscriptions})


def subscription_accept_view(request, pk):
    """Accept an association's subscription request."""
    client = APIClient(request)

    code, resp = client.post(f"/api/subscriptions/{pk}/action/", json={"action": "accept"})
    if code == 200:
        messages.success(request, "Abonnement validé ! Les crédits solidaires ont été crédités à l'association.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("merchant-subscriptions")


def subscription_reject_view(request, pk):
    """Reject an association's subscription request with reason."""
    client = APIClient(request)
    reason = request.POST.get("reason", "Refusé par le commerçant.")

    code, resp = client.post(
        f"/api/subscriptions/{pk}/action/",
        json={"action": "reject", "reason": reason},
    )
    if code == 200:
        messages.success(request, "Demande d'abonnement refusée.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("merchant-subscriptions")


def reservations_view(request):
    """View and respond to incoming reservations from associations."""
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
    return render(request, "merchant/reservations.html", context)


def reservation_accept_view(request, pk):
    """Accept reservation and confirm scheduled collection."""
    client = APIClient(request)
    notes = request.POST.get("notes", "Commande préparée pour collecte.")

    code, resp = client.post(
        f"/api/reservations/{pk}/action/",
        json={"action": "accept", "notes": notes},
    )
    if code == 200:
        messages.success(request, "Réservation acceptée ! La collecte est désormais planifiée.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("merchant-reservations")


def reservation_reject_view(request, pk):
    """Reject reservation with mandatory reason."""
    client = APIClient(request)
    reason = request.POST.get("reason", "").strip()

    if not reason:
        messages.error(request, "Veuillez préciser le motif de refus.")
        return redirect("merchant-reservations")

    code, resp = client.post(
        f"/api/reservations/{pk}/action/",
        json={"action": "reject", "reason": reason},
    )
    if code == 200:
        messages.success(request, "Réservation refusée. Les crédits ont été remboursés à l'association.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("merchant-reservations")


def collections_view(request):
    """Manage and confirm collections."""
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
    return render(request, "merchant/collections.html", context)


def collection_complete_view(request, pk):
    """Confirm a collection was completed."""
    client = APIClient(request)
    notes = request.POST.get("notes", "Collecte remise avec succès.")

    code, resp = client.post(
        f"/api/collections/{pk}/action/",
        json={"action": "complete", "notes": notes},
    )
    if code == 200:
        messages.success(request, "Collecte validée avec succès ! Les denrées ont été transmises.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("merchant-collections")


def collection_miss_view(request, pk):
    """Mark collection as missed."""
    client = APIClient(request)
    notes = request.POST.get("notes", "L'association ne s'est pas présentée.")

    code, resp = client.post(
        f"/api/collections/{pk}/action/",
        json={"action": "miss", "notes": notes},
    )
    if code == 200:
        messages.warning(request, "Collecte marquée comme manquée. Les stocks ont été restaurés.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("merchant-collections")


def profile_view(request):
    """Merchant business profile settings."""
    client = APIClient(request)

    _, merchant = client.get("/api/merchants/me/")

    if request.method == "POST":
        data = {
            "business_name": request.POST.get("business_name", "").strip(),
            "tax_id": request.POST.get("tax_id", "").strip(),
            "city": request.POST.get("city", "").strip(),
            "address": request.POST.get("address", "").strip(),
            "postal_code": request.POST.get("postal_code", "").strip(),
            "opening_hours": request.POST.get("opening_hours", "").strip(),
            "website": request.POST.get("website", "").strip(),
            "description": request.POST.get("description", "").strip(),
        }
        files = {}
        if request.FILES.get("logo"):
            files["logo"] = request.FILES["logo"]

        code, resp = client.patch("/api/merchants/me/", data=data, files=files)
        if code == 200:
            messages.success(request, "Profil commerçant mis à jour.")
            return redirect("merchant-profile")
        else:
            messages.error(request, format_api_errors(resp))

    return render(request, "merchant/profile.html", {"merchant": merchant})
