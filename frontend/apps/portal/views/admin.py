from django.contrib import messages
from django.shortcuts import redirect, render
from apps.portal.api_client import APIClient, format_api_errors


def dashboard_view(request):
    """Admin Dashboard: Global metrics, recent items, activity feed."""
    client = APIClient(request)

    _, stats = client.get("/api/stats/admin/")
    if not isinstance(stats, dict):
        stats = {}

    _, recent_users_data = client.get("/api/auth/users/", params={"page_size": 5})
    recent_users = recent_users_data.get("results", []) if isinstance(recent_users_data, dict) else []

    _, recent_products_data = client.get("/api/products/", params={"page_size": 5})
    recent_products = recent_products_data.get("results", []) if isinstance(recent_products_data, dict) else []

    context = {
        "stats": stats,
        "recent_users": recent_users,
        "recent_products": recent_products,
    }
    return render(request, "admin_portal/dashboard.html", context)


def users_view(request):
    """Manage users, associations, and merchants with approval actions."""
    client = APIClient(request)

    params = {}
    role = request.GET.get("role")
    if role:
        params["role"] = role
    status_param = request.GET.get("status")
    if status_param:
        params["status"] = status_param
    q = request.GET.get("q")
    if q:
        params["q"] = q

    _, data = client.get("/api/auth/users/", params=params)
    users = data.get("results", []) if isinstance(data, dict) else []

    context = {
        "users": users,
        "selected_role": role or "",
        "selected_status": status_param or "",
        "search_query": q or "",
    }
    return render(request, "admin_portal/users.html", context)


def user_review_view(request, pk):
    """Approve or reject association/merchant account."""
    client = APIClient(request)

    action = request.POST.get("action")  # 'approve' or 'reject'
    reason = request.POST.get("reason", "")

    code, resp = client.post(
        f"/api/auth/users/{pk}/review/",
        json={"action": action, "reason": reason},
    )
    if code == 200:
        messages.success(request, f"Le compte utilisateur #{pk} a été { 'approuvé' if action == 'approve' else 'refusé' }.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("admin-users")


def products_view(request):
    """Moderate products and view all platform listings."""
    client = APIClient(request)

    params = {}
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

    context = {
        "products": products,
        "selected_status": status_param or "",
        "selected_kind": kind_param or "",
        "search_query": q or "",
    }
    return render(request, "admin_portal/products.html", context)


def product_moderate_view(request, pk):
    """Approve or reject a product listing."""
    client = APIClient(request)

    action = request.POST.get("action")
    reason = request.POST.get("reason", "")

    code, resp = client.post(
        f"/api/products/{pk}/moderate/",
        json={"action": action, "reason": reason},
    )
    if code == 200:
        messages.success(request, f"Le produit #{pk} a été { 'validé' if action == 'approve' else 'rejeté' }.")
    else:
        messages.error(request, format_api_errors(resp))
    return redirect("admin-products")


def categories_view(request):
    """Manage product categories."""
    client = APIClient(request)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            name = request.POST.get("name", "").strip()
            description = request.POST.get("description", "").strip()
            code, resp = client.post("/api/categories/", json={"name": name, "description": description})
            if code == 201:
                messages.success(request, f"Catégorie « {name} » ajoutée !")
            else:
                messages.error(request, format_api_errors(resp))
        elif action == "delete":
            cat_id = request.POST.get("category_id")
            code, resp = client.delete(f"/api/categories/{cat_id}/")
            if code == 204:
                messages.success(request, "Catégorie supprimée.")
            else:
                messages.error(request, format_api_errors(resp))
        return redirect("admin-categories")

    _, data = client.get("/api/categories/")
    categories = data if isinstance(data, list) else []

    return render(request, "admin_portal/categories.html", {"categories": categories})


def reservations_view(request):
    """Monitor all reservations and collections platform-wide."""
    client = APIClient(request)

    params = {}
    status_param = request.GET.get("status")
    if status_param:
        params["status"] = status_param

    _, data = client.get("/api/reservations/", params=params)
    reservations = data.get("results", []) if isinstance(data, dict) else []

    _, col_data = client.get("/api/collections/")
    collections = col_data.get("results", []) if isinstance(col_data, dict) else []

    context = {
        "reservations": reservations,
        "collections": collections,
        "selected_status": status_param or "",
    }
    return render(request, "admin_portal/reservations.html", context)


def distributions_view(request):
    """Monitor distributions and beneficiaries platform-wide."""
    client = APIClient(request)

    _, dist_data = client.get("/api/distributions/")
    distributions = dist_data.get("results", []) if isinstance(dist_data, dict) else []

    _, ben_data = client.get("/api/beneficiaries/")
    beneficiaries = ben_data.get("results", []) if isinstance(ben_data, dict) else []

    context = {
        "distributions": distributions,
        "beneficiaries": beneficiaries,
    }
    return render(request, "admin_portal/distributions.html", context)


def subscriptions_view(request):
    """Monitor subscriptions and solidarity plans."""
    client = APIClient(request)

    _, sub_data = client.get("/api/subscriptions/")
    subscriptions = sub_data.get("results", []) if isinstance(sub_data, dict) else []

    _, plan_data = client.get("/api/plans/")
    plans = plan_data.get("results", []) if isinstance(plan_data, dict) else []

    context = {
        "subscriptions": subscriptions,
        "plans": plans,
    }
    return render(request, "admin_portal/subscriptions.html", context)


def credit_adjust_view(request):
    """Grant or adjust credits for an association."""
    client = APIClient(request)

    if request.method == "POST":
        payload = {
            "association_id": int(request.POST.get("association_id")),
            "amount": request.POST.get("amount"),
            "tx_type": request.POST.get("tx_type", "grant"),
            "description": request.POST.get("description", "Ajustement administratif"),
        }

        code, resp = client.post("/api/credits/adjust/", json=payload)
        if code == 201:
            messages.success(request, f"Crédits {payload['amount']} alloués avec succès !")
        else:
            messages.error(request, format_api_errors(resp))

    return redirect("admin-subscriptions")


def activity_logs_view(request):
    """View audit trail of platform events."""
    client = APIClient(request)

    _, data = client.get("/api/activity/")
    activities = data.get("results", []) if isinstance(data, dict) else []

    return render(request, "admin_portal/activity.html", {"activities": activities})
