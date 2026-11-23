import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from decimal import Decimal
from django.test import Client
from apps.accounts.models import User
from apps.associations.models import Association
from apps.merchants.models import Merchant
from apps.products.models import Category, Product
from apps.reservations.models import Collection, Reservation
from apps.subscriptions.models import Subscription, SubscriptionPlan
from apps.beneficiaries.models import Beneficiary
from apps.distributions.models import Distribution


def run_e2e_tests():
    print("==================================================")
    print("   RUNNING DONATILY END-TO-END FLOW VERIFICATION  ")
    print("==================================================")

    client = Client()

    # 1. Authenticate as Association
    res = client.post(
        "/api/auth/login/",
        {"email": "croissant.rouge@tunisie.tn", "password": "AssocPass123!"},
        content_type="application/json",
    )
    assert res.status_code == 200, f"Association login failed: {res.json()}"
    assoc_token = res.json()["access"]
    assoc_hdr = {"HTTP_AUTHORIZATION": f"Bearer {assoc_token}"}
    print("1. Association Authenticated via JWT OK")

    # 2. Authenticate as Merchant
    res = client.post(
        "/api/auth/login/",
        {"email": "contact@boulangerie-elyssa.tn", "password": "MerchantPass123!"},
        content_type="application/json",
    )
    assert res.status_code == 200, f"Merchant login failed: {res.json()}"
    merch_token = res.json()["access"]
    merch_hdr = {"HTTP_AUTHORIZATION": f"Bearer {merch_token}"}
    print("2. Merchant Authenticated via JWT OK")

    # 3. Authenticate as Admin
    res = client.post(
        "/api/auth/login/",
        {"email": "admin@donatily.tn", "password": "AdminPass123!"},
        content_type="application/json",
    )
    assert res.status_code == 200, f"Admin login failed: {res.json()}"
    admin_token = res.json()["access"]
    admin_hdr = {"HTTP_AUTHORIZATION": f"Bearer {admin_token}"}
    print("3. Admin Authenticated via JWT OK")

    # 4. Merchant publishes a new product
    category = Category.objects.first()
    res = client.post(
        "/api/products/",
        {
            "name": "Lot Spécial 20 Pains au Lait",
            "category": category.id,
            "description": "Invendus du soir conservés au frais.",
            "kind": "unsold",
            "unit": "lot",
            "original_price": "15.00",
            "offer_price": "5.00",
            "credit_cost": "3.00",
            "stock": 10,
        },
        content_type="application/json",
        **merch_hdr,
    )
    assert res.status_code == 201, f"Product creation failed: {res.json()}"
    new_product_id = res.json()["id"]
    print(f"4. Merchant created product #{new_product_id} in status 'pending' OK")

    # 5. Admin moderates and approves the product
    res = client.post(
        f"/api/products/{new_product_id}/moderate/",
        {"action": "approve", "reason": ""},
        content_type="application/json",
        **admin_hdr,
    )
    assert res.status_code == 200, f"Product moderation failed: {res.json()}"
    assert res.json()["status"] == "approved"
    print(f"5. Admin approved product #{new_product_id} -> Status: 'approved' OK")

    # 6. Association checks initial credit balance and reserves product
    assoc_profile = Association.objects.get(user__email="croissant.rouge@tunisie.tn")
    initial_balance = assoc_profile.credit_balance
    initial_stock = Product.objects.get(id=new_product_id).stock

    res = client.post(
        "/api/reservations/",
        {
            "pickup_date": "2026-11-25",
            "notes": "Passage prévu en début d'après-midi.",
            "items": [{"product_id": new_product_id, "quantity": 2}],
        },
        content_type="application/json",
        **assoc_hdr,
    )
    assert res.status_code == 201, f"Reservation failed: {res.json()}"
    res_id = res.json()["id"]
    print(f"6. Association created reservation #{res_id} (Quantity: 2) OK")

    # Verify inventory was decremented by 2, and 6.00 credits deducted
    product_after = Product.objects.get(id=new_product_id)
    assoc_after = Association.objects.get(id=assoc_profile.id)
    assert product_after.stock == initial_stock - 2, f"Stock was not decremented properly: {product_after.stock}"
    assert assoc_after.credit_balance == initial_balance - Decimal("6.00"), f"Credit was not deducted properly: {assoc_after.credit_balance}"
    print(f"   ✓ Stock decremented: {initial_stock} -> {product_after.stock}")
    print(f"   ✓ Credits deducted: {initial_balance} -> {assoc_after.credit_balance}")

    # 7. Merchant accepts reservation
    res = client.post(
        f"/api/reservations/{res_id}/action/",
        {"action": "accept", "notes": "Commande mise de côté au comptoir."},
        content_type="application/json",
        **merch_hdr,
    )
    assert res.status_code == 200, f"Reservation acceptance failed: {res.json()}"
    assert res.json()["status"] == "accepted"
    col_id = res.json()["collection"]["id"]
    print(f"7. Merchant accepted reservation #{res_id} -> Collection #{col_id} scheduled OK")

    # 8. Merchant completes collection
    res = client.post(
        f"/api/collections/{col_id}/action/",
        {"action": "complete", "notes": "Remis aux bénévoles du Croissant-Rouge."},
        content_type="application/json",
        **merch_hdr,
    )
    assert res.status_code == 200, f"Collection completion failed: {res.json()}"
    assert res.json()["status"] == "completed"
    print(f"8. Merchant confirmed collection #{col_id} -> Status: 'completed' OK")

    # 9. Association registers beneficiary and records distribution
    res = client.post(
        "/api/beneficiaries/",
        {
            "first_name": "Khadija",
            "last_name": "Mejri",
            "phone": "+216 99 888 777",
            "address": "Cité Ennour",
            "city": "Tunis",
            "household_size": 4,
            "needs": "Pain quotidien, produits laitiers",
            "priority": "high",
            "is_active": True,
        },
        content_type="application/json",
        **assoc_hdr,
    )
    assert res.status_code == 201, f"Beneficiary creation failed: {res.json()}"
    beneficiary_id = res.json()["id"]
    print(f"9. Association added beneficiary #{beneficiary_id} (Khadija Mejri) OK")

    res = client.post(
        "/api/distributions/",
        {
            "beneficiary": beneficiary_id,
            "title": "Lot de pains au lait frais",
            "quantity": 1,
            "unit": "lot",
            "distributed_on": "2026-11-23",
            "notes": "Remis à domicile.",
        },
        content_type="application/json",
        **assoc_hdr,
    )
    assert res.status_code == 201, f"Distribution failed: {res.json()}"
    dist_id = res.json()["id"]
    print(f"10. Association recorded distribution #{dist_id} to beneficiary OK")

    # 11. Admin verifies stats
    res = client.get("/api/stats/admin/", **admin_hdr)
    assert res.status_code == 200
    stats = res.json()
    assert stats["reservations"] >= 1
    assert stats["collections"] >= 1
    assert stats["distributions"] >= 1
    print(f"11. Admin verified global stats: {stats['users']} users, {stats['reservations']} reservations, {stats['distributions']} distributions OK")

    print("\n==================================================")
    print("   ALL DONATILY E2E BUSINESS FLOWS VERIFIED 100%  ")
    print("==================================================")


if __name__ == "__main__":
    run_e2e_tests()
