import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.test import Client


def run_frontend_checks():
    client = Client()

    # 1. Landing Page
    res = client.get("/")
    assert res.status_code == 200, f"Landing page failed: {res.status_code}"
    assert "DONATILY" in res.content.decode("utf-8")
    print("✓ Frontend Landing page (/) 200 OK")

    # 2. Explore products
    res = client.get("/explore/products/")
    assert res.status_code == 200, f"Explore products failed: {res.status_code}"
    print("✓ Frontend Explore products (/explore/products/) 200 OK")

    # 3. Explore merchants
    res = client.get("/explore/merchants/")
    assert res.status_code == 200, f"Explore merchants failed: {res.status_code}"
    print("✓ Frontend Explore merchants (/explore/merchants/) 200 OK")

    # 4. Login page
    res = client.get("/login/")
    assert res.status_code == 200, f"Login page failed: {res.status_code}"
    print("✓ Frontend Login page (/login/) 200 OK")

    # 5. Register association
    res = client.get("/register/association/")
    assert res.status_code == 200, f"Register association page failed: {res.status_code}"
    print("✓ Frontend Register association page 200 OK")

    # 6. Register merchant
    res = client.get("/register/merchant/")
    assert res.status_code == 200, f"Register merchant page failed: {res.status_code}"
    print("✓ Frontend Register merchant page 200 OK")

    # 7. Protected route redirection when unauthenticated
    res = client.get("/association/")
    assert res.status_code == 302, f"Protected route should redirect to login: {res.status_code}"
    assert "/login/" in res["Location"]
    print("✓ Role protection middleware redirect (/association/ -> /login/) 302 OK")

    # 8. Simulate authenticated Association session
    session = client.session
    session["access_token"] = "fake-jwt-token"
    session["user"] = {
        "id": 2,
        "email": "croissant.rouge@tunisie.tn",
        "display_name": "Croissant-Rouge Tunisien",
        "role": "association",
    }
    session.save()

    res = client.get("/association/")
    assert res.status_code == 200, f"Association dashboard failed: {res.status_code}"
    print("✓ Authenticated Association Dashboard (/association/) 200 OK")

    res = client.get("/association/products/")
    assert res.status_code == 200
    print("✓ Authenticated Association Products Catalog (/association/products/) 200 OK")

    res = client.get("/association/reservations/")
    assert res.status_code == 200
    print("✓ Authenticated Association Reservations (/association/reservations/) 200 OK")

    res = client.get("/association/beneficiaries/")
    assert res.status_code == 200
    print("✓ Authenticated Association Beneficiaries (/association/beneficiaries/) 200 OK")

    # 9. Simulate authenticated Merchant session
    session["user"] = {
        "id": 3,
        "email": "contact@boulangerie-elyssa.tn",
        "display_name": "Boulangerie Artisanale Elyssa",
        "role": "merchant",
    }
    session.save()

    res = client.get("/merchant/")
    assert res.status_code == 200
    print("✓ Authenticated Merchant Dashboard (/merchant/) 200 OK")

    res = client.get("/merchant/products/")
    assert res.status_code == 200
    print("✓ Authenticated Merchant Products (/merchant/products/) 200 OK")

    res = client.get("/merchant/plans/")
    assert res.status_code == 200
    print("✓ Authenticated Merchant Plans (/merchant/plans/) 200 OK")

    # 10. Simulate authenticated Admin session
    session["user"] = {
        "id": 1,
        "email": "admin@donatily.tn",
        "display_name": "Sami Ben Amor",
        "role": "admin",
    }
    session.save()

    res = client.get("/admin-portal/")
    assert res.status_code == 200
    print("✓ Authenticated Admin Dashboard (/admin-portal/) 200 OK")

    res = client.get("/admin-portal/users/")
    assert res.status_code == 200
    print("✓ Authenticated Admin Users (/admin-portal/users/) 200 OK")

    res = client.get("/admin-portal/products/")
    assert res.status_code == 200
    print("✓ Authenticated Admin Products Moderation (/admin-portal/products/) 200 OK")

    print("\n========================================================")
    print("  ALL FRONTEND TEMPLATES & VIEW CHECKS PASSED 100%!     ")
    print("========================================================")


if __name__ == "__main__":
    run_frontend_checks()
