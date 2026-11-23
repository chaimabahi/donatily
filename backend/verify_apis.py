import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.test import Client


def run_checks():
    client = Client()

    # 1. Health
    res = client.get("/api/health/")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print("✓ /api/health/ 200 OK")

    # 2. Login as Association
    res = client.post(
        "/api/auth/login/",
        {"email": "croissant.rouge@tunisie.tn", "password": "AssocPass123!"},
        content_type="application/json",
    )
    assert res.status_code == 200, f"Login failed: {res.status_code} {res.json()}"
    assoc_token = res.json()["access"]
    assoc_header = {"HTTP_AUTHORIZATION": f"Bearer {assoc_token}"}
    print("✓ /api/auth/login/ (Association) 200 OK")

    # 3. Login as Merchant
    res = client.post(
        "/api/auth/login/",
        {"email": "contact@boulangerie-elyssa.tn", "password": "MerchantPass123!"},
        content_type="application/json",
    )
    assert res.status_code == 200, f"Merchant login failed: {res.status_code}"
    merch_token = res.json()["access"]
    merch_header = {"HTTP_AUTHORIZATION": f"Bearer {merch_token}"}
    print("✓ /api/auth/login/ (Merchant) 200 OK")

    # 4. Login as Admin
    res = client.post(
        "/api/auth/login/",
        {"email": "admin@donatily.tn", "password": "AdminPass123!"},
        content_type="application/json",
    )
    assert res.status_code == 200, f"Admin login failed: {res.status_code}"
    admin_token = res.json()["access"]
    admin_header = {"HTTP_AUTHORIZATION": f"Bearer {admin_token}"}
    print("✓ /api/auth/login/ (Admin) 200 OK")

    # 5. Public Categories & Products
    res = client.get("/api/categories/")
    assert res.status_code == 200, f"Categories failed: {res.status_code}"
    categories = res.json()
    print(f"✓ /api/categories/ 200 OK ({len(categories)} categories found)")

    res = client.get("/api/products/")
    assert res.status_code == 200, f"Products failed: {res.status_code}"
    products_count = res.json()["count"]
    print(f"✓ /api/products/ 200 OK ({products_count} approved products found)")

    # 6. Plans
    res = client.get("/api/plans/")
    assert res.status_code == 200, f"Plans failed: {res.status_code}"
    plans_count = res.json()["count"]
    print(f"✓ /api/plans/ 200 OK ({plans_count} plans found)")

    # 7. Association Stats & Beneficiaries & Reservations
    res = client.get("/api/stats/association/", **assoc_header)
    assert res.status_code == 200, f"Association stats failed: {res.status_code}"
    print(f"✓ /api/stats/association/ 200 OK (balance: {res.json()['credit_balance']})")

    res = client.get("/api/beneficiaries/", **assoc_header)
    assert res.status_code == 200, f"Beneficiaries failed: {res.status_code}"
    print(f"✓ /api/beneficiaries/ 200 OK ({res.json()['count']} beneficiaries)")

    res = client.get("/api/reservations/", **assoc_header)
    assert res.status_code == 200, f"Reservations failed: {res.status_code}"
    print(f"✓ /api/reservations/ 200 OK ({res.json()['count']} reservations)")

    # 8. Merchant Stats & Collections
    res = client.get("/api/stats/merchant/", **merch_header)
    assert res.status_code == 200, f"Merchant stats failed: {res.status_code}"
    print(f"✓ /api/stats/merchant/ 200 OK (products: {res.json()['products']})")

    res = client.get("/api/collections/", **merch_header)
    assert res.status_code == 200, f"Collections failed: {res.status_code}"
    print(f"✓ /api/collections/ 200 OK ({res.json()['count']} collections)")

    # 9. Admin Stats & Users
    res = client.get("/api/stats/admin/", **admin_header)
    assert res.status_code == 200, f"Admin stats failed: {res.status_code}"
    print(f"✓ /api/stats/admin/ 200 OK (total users: {res.json()['users']})")

    # 10. Swagger schema
    res = client.get("/api/schema/")
    assert res.status_code == 200, f"OpenAPI schema failed: {res.status_code}"
    print("✓ /api/schema/ 200 OK (OpenAPI / Swagger spec generated successfully)")

    print("\n=============================================")
    print("  ALL BACKEND API VERIFICATION TESTS PASSED! ")
    print("=============================================")


if __name__ == "__main__":
    run_checks()
