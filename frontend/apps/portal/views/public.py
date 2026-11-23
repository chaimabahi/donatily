from django.shortcuts import render

from apps.portal.api_client import APIClient


def landing_view(request):
    """Public landing page with mission, metrics, featured offers and partners."""
    client = APIClient(request)

    # Fetch approved categories and highlighted products
    _, categories_data = client.get("/api/categories/")
    categories = categories_data if isinstance(categories_data, list) else []

    _, products_data = client.get("/api/products/", params={"page_size": 6})
    products = products_data.get("results", []) if isinstance(products_data, dict) else []

    _, merchants_data = client.get("/api/merchants/", params={"page_size": 4})
    merchants = merchants_data.get("results", []) if isinstance(merchants_data, dict) else []

    context = {
        "categories": categories,
        "featured_products": products,
        "partner_merchants": merchants,
        "total_associations_count": 48,
        "total_merchants_count": 86,
        "total_saved_meals": 14250,
        "total_kg_co2": 8900,
    }
    return render(request, "public/index.html", context)


def explore_products_view(request):
    """Public catalog of available solidarity offers and donations."""
    client = APIClient(request)

    # Get query params
    params = {}
    for key in ["category", "kind", "city", "q", "page"]:
        val = request.GET.get(key)
        if val:
            params[key] = val

    _, categories_data = client.get("/api/categories/")
    categories = categories_data if isinstance(categories_data, list) else []

    _, products_data = client.get("/api/products/", params=params)
    products = products_data.get("results", []) if isinstance(products_data, dict) else []
    count = products_data.get("count", len(products)) if isinstance(products_data, dict) else len(products)

    context = {
        "categories": categories,
        "products": products,
        "total_count": count,
        "selected_category": request.GET.get("category", ""),
        "selected_kind": request.GET.get("kind", ""),
        "selected_city": request.GET.get("city", ""),
        "search_query": request.GET.get("q", ""),
    }
    return render(request, "public/explore_products.html", context)


def explore_merchants_view(request):
    """Public directory of partner businesses across Tunisian governorates."""
    client = APIClient(request)

    params = {}
    for key in ["city", "q", "page"]:
        val = request.GET.get(key)
        if val:
            params[key] = val

    _, merchants_data = client.get("/api/merchants/", params=params)
    merchants = merchants_data.get("results", []) if isinstance(merchants_data, dict) else []
    count = merchants_data.get("count", len(merchants)) if isinstance(merchants_data, dict) else len(merchants)

    context = {
        "merchants": merchants,
        "total_count": count,
        "selected_city": request.GET.get("city", ""),
        "search_query": request.GET.get("q", ""),
    }
    return render(request, "public/explore_merchants.html", context)
