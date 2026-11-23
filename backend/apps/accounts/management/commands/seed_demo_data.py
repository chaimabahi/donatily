import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import ActivityLog, Notification, User
from apps.associations.models import Association
from apps.beneficiaries.models import Beneficiary
from apps.distributions.models import Distribution
from apps.merchants.models import Merchant
from apps.products.models import Category, Product
from apps.reservations.models import Collection, Reservation, ReservationItem
from apps.subscriptions.models import CreditTransaction, Subscription, SubscriptionPlan


class Command(BaseCommand):
    help = "Seed database with initial Tunisian solidarity demonstration data."

    def handle(self, *args, **options):
        self.stdout.write("Seeding Donatily database...")

        # 1. Admin
        admin_user, _ = User.objects.get_or_create(
            email="admin@donatily.tn",
            defaults={
                "first_name": "Sami",
                "last_name": "Ben Amor",
                "role": User.Role.ADMIN,
                "phone": "+216 71 100 200",
                "is_staff": True,
                "is_superuser": True,
                "is_verified": True,
            },
        )
        admin_user.set_password("AdminPass123!")
        admin_user.save()

        # 2. Categories
        categories_data = [
            ("Boulangerie & Pains", "boulangerie-pains", "Pains artisanaux, baguettes tradition, viennoiseries du jour."),
            ("Fruits & Légumes Frais", "fruits-legumes", "Surplus maraîchers locaux, cageots de saison."),
            ("Produits Laitiers & Frais", "produits-laitiers", "Laits, yaourts, fromages locaux à dates courtes."),
            ("Épicerie Sèche & Féculents", "epicerie-seche", "Semoules, pâtes, riz, légumineuses et conserves."),
            ("Plats & Traiteur", "plats-traiteur", "Plats préparés sains non vendus le jour même."),
            ("Hygiène & Soins", "hygiene-soins", "Savons, produits de première nécessité, couches."),
        ]
        cat_map = {}
        for name, slug, desc in categories_data:
            cat, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "description": desc},
            )
            cat_map[slug] = cat

        # 3. Merchants
        merchants_data = [
            {
                "email": "contact@boulangerie-elyssa.tn",
                "first_name": "Kamel",
                "last_name": "Mansour",
                "phone": "+216 71 888 999",
                "business_name": "Boulangerie Artisanale Elyssa",
                "tax_id": "MF-1029384/A/M/000",
                "city": "Tunis",
                "address": "14 Avenue Habib Bourguiba, Tunis",
                "description": "Boulangerie et pâtisserie artisanale engagée contre le gaspillage alimentaire.",
                "opening_hours": "06:00 - 20:00",
            },
            {
                "email": "superette.carthage@gmail.com",
                "first_name": "Leila",
                "last_name": "Trabelsi",
                "phone": "+216 71 777 666",
                "business_name": "Supérette Solidaire Carthage",
                "tax_id": "MF-2039485/B/M/000",
                "city": "La Marsa",
                "address": "5 Rue de la République, La Marsa",
                "description": "Commerce de proximité solidaire avec redistribution quotidienne des invendus.",
                "opening_hours": "08:00 - 21:00",
            },
            {
                "email": "maraicher.capbon@topnet.tn",
                "first_name": "Mounir",
                "last_name": "Gharbi",
                "phone": "+216 72 333 444",
                "business_name": "Les Maraîchers du Cap Bon",
                "tax_id": "MF-3049586/C/M/000",
                "city": "Nabeul",
                "address": "Route de Tunis Km 4, Nabeul",
                "description": "Producteur agricole regroupant 12 fermes maraîchères solidaires.",
                "opening_hours": "07:00 - 18:00",
            },
            {
                "email": "bio.sahel@gmail.com",
                "first_name": "Fatma",
                "last_name": "Cherif",
                "phone": "+216 73 555 111",
                "business_name": "Épicerie Bio du Sahel",
                "tax_id": "MF-4059687/D/M/000",
                "city": "Sousse",
                "address": "22 Boulevard 14 Janvier, Sousse",
                "description": "Épicerie fine biologique et produits du terroir tunisien.",
                "opening_hours": "08:30 - 20:30",
            },
        ]

        merchant_objs = {}
        for md in merchants_data:
            u, _ = User.objects.get_or_create(
                email=md["email"],
                defaults={
                    "first_name": md["first_name"],
                    "last_name": md["last_name"],
                    "role": User.Role.MERCHANT,
                    "phone": md["phone"],
                    "is_verified": True,
                },
            )
            u.set_password("MerchantPass123!")
            u.save()

            m, _ = Merchant.objects.get_or_create(
                user=u,
                defaults={
                    "business_name": md["business_name"],
                    "tax_id": md["tax_id"],
                    "city": md["city"],
                    "address": md["address"],
                    "description": md["description"],
                    "opening_hours": md["opening_hours"],
                    "status": Merchant.Status.APPROVED,
                },
            )
            merchant_objs[md["business_name"]] = m

        # 4. Associations
        associations_data = [
            {
                "email": "croissant.rouge@tunisie.tn",
                "first_name": "Hichem",
                "last_name": "Dridi",
                "phone": "+216 71 325 555",
                "name": "Croissant-Rouge Tunisien - Section Tunis",
                "reg": "JORT-CRT-1956-001",
                "city": "Tunis",
                "address": "19 Rue d'Angleterre, Tunis",
                "description": "Organisation humanitaire d'aide d'urgence et d'assistance aux familles vulnérables.",
                "credits": Decimal("250.00"),
            },
            {
                "email": "un_sourire_tous@gmail.com",
                "first_name": "Salma",
                "last_name": "Bouazizi",
                "phone": "+216 74 220 330",
                "name": "Un Sourire Pour Tous Sfax",
                "reg": "JORT-USPT-2012-044",
                "city": "Sfax",
                "address": "Route de Téniour Km 2.5, Sfax",
                "description": "Association d'aide aux enfants scolarisés défavorisés et paniers de denrées.",
                "credits": Decimal("180.00"),
            },
            {
                "email": "club.solidarite.insat@gmail.com",
                "first_name": "Yassine",
                "last_name": "Ayari",
                "phone": "+216 98 444 333",
                "name": "Club Solidarité INSAT",
                "reg": "JORT-CSIN-2018-092",
                "city": "Ariana",
                "address": "Centre Urbain Nord, INSAT, Ariana",
                "description": "Club associatif étudiant luttant contre la précarité étudiante et locale.",
                "credits": Decimal("120.00"),
            },
            {
                "email": "espoir.enfance@planet.tn",
                "first_name": "Amira",
                "last_name": "Jlassi",
                "phone": "+216 73 440 220",
                "name": "Espoir & Solidarité Sousse",
                "reg": "JORT-ESSO-2015-112",
                "city": "Sousse",
                "address": "Avenue Léopold Senghor, Sousse",
                "description": "Accompagnement social, cantines solidaires et fournitures d'hygiène.",
                "credits": Decimal("90.00"),
            },
        ]

        assoc_objs = {}
        for ad in associations_data:
            u, _ = User.objects.get_or_create(
                email=ad["email"],
                defaults={
                    "first_name": ad["first_name"],
                    "last_name": ad["last_name"],
                    "role": User.Role.ASSOCIATION,
                    "phone": ad["phone"],
                    "is_verified": True,
                },
            )
            u.set_password("AssocPass123!")
            u.save()

            a, _ = Association.objects.get_or_create(
                user=u,
                defaults={
                    "name": ad["name"],
                    "registration_number": ad["reg"],
                    "city": ad["city"],
                    "address": ad["address"],
                    "description": ad["description"],
                    "credit_balance": ad["credits"],
                    "status": Association.Status.APPROVED,
                },
            )
            assoc_objs[ad["name"]] = a

        # 5. Subscription Plans
        plans_data = [
            {
                "merchant": merchant_objs["Boulangerie Artisanale Elyssa"],
                "name": "Formule Pain & Viennoiseries Solidaire",
                "description": "Donne accès à 25 lots quotidiens de pains artisanaux et viennoiseries fraîches non vendues.",
                "price": Decimal("60.00"),
                "credits": Decimal("80.00"),
                "duration_days": 30,
            },
            {
                "merchant": merchant_objs["Supérette Solidaire Carthage"],
                "name": "Panier Fraîcheur & Épicerie",
                "description": "Accès prioritaire aux arrivages de produits frais, crèmerie et épicerie sèche à prix solidaire.",
                "price": Decimal("120.00"),
                "credits": Decimal("160.00"),
                "duration_days": 30,
            },
            {
                "merchant": merchant_objs["Les Maraîchers du Cap Bon"],
                "name": "Cagettes Maraîchères Hebdomadaires",
                "description": "Redistribution hebdomadaire de légumes et fruits de saison directement issus des producteurs.",
                "price": Decimal("150.00"),
                "credits": Decimal("200.00"),
                "duration_days": 30,
            },
        ]

        plan_objs = []
        for pd in plans_data:
            p, _ = SubscriptionPlan.objects.get_or_create(
                merchant=pd["merchant"],
                name=pd["name"],
                defaults={
                    "description": pd["description"],
                    "price": pd["price"],
                    "credits": pd["credits"],
                    "duration_days": pd["duration_days"],
                    "is_active": True,
                },
            )
            plan_objs.append(p)

        # 6. Active Subscriptions
        today = timezone.localdate()
        crt = assoc_objs["Croissant-Rouge Tunisien - Section Tunis"]
        sub1, _ = Subscription.objects.get_or_create(
            association=crt,
            plan=plan_objs[0],
            defaults={
                "status": Subscription.Status.ACTIVE,
                "start_date": today - datetime.timedelta(days=5),
                "end_date": today + datetime.timedelta(days=25),
            },
        )

        uspt = assoc_objs["Un Sourire Pour Tous Sfax"]
        sub2, _ = Subscription.objects.get_or_create(
            association=uspt,
            plan=plan_objs[1],
            defaults={
                "status": Subscription.Status.ACTIVE,
                "start_date": today - datetime.timedelta(days=10),
                "end_date": today + datetime.timedelta(days=20),
            },
        )

        # 7. Products
        products_data = [
            # Boulangerie Elyssa
            (
                merchant_objs["Boulangerie Artisanale Elyssa"],
                cat_map["boulangerie-pains"],
                "Lot de 10 Baguettes Tradition",
                "Baguettes traditionnelles au levain naturel cuites le matin même.",
                Product.Kind.DONATION,
                Decimal("0.00"),
                Decimal("0.00"),
                Decimal("0.00"),
                15,
                Product.Unit.LOT,
            ),
            (
                merchant_objs["Boulangerie Artisanale Elyssa"],
                cat_map["boulangerie-pains"],
                "Plateau de Croissants et Pains au Chocolat",
                "Assortiment de 12 viennoiseries pur beurre du jour.",
                Product.Kind.UNSOLD,
                Decimal("24.00"),
                Decimal("8.00"),
                Decimal("5.00"),
                8,
                Product.Unit.LOT,
            ),
            # Supérette Carthage
            (
                merchant_objs["Supérette Solidaire Carthage"],
                cat_map["produits-laitiers"],
                "Packs de Yaourts Nature & Arôme (Lot de 16)",
                "Produits laitiers avec DLC à 3 jours, conservés en chaîne de froid certifiée.",
                Product.Kind.UNSOLD,
                Decimal("16.00"),
                Decimal("4.00"),
                Decimal("4.00"),
                20,
                Product.Unit.PACK,
            ),
            (
                merchant_objs["Supérette Solidaire Carthage"],
                cat_map["epicerie-seche"],
                "Carton de Semoule Fine et Pâtes Traditionnelles",
                "Paquets de 1kg couscous fin et pâtes tunisiennes.",
                Product.Kind.DONATION,
                Decimal("0.00"),
                Decimal("0.00"),
                Decimal("0.00"),
                30,
                Product.Unit.PACK,
            ),
            (
                merchant_objs["Supérette Solidaire Carthage"],
                cat_map["hygiene-soins"],
                "Packs de Savon Traditionnel et Gel Douche",
                "Produits d'hygiène corporelle pour familles.",
                Product.Kind.DISCOUNT,
                Decimal("35.00"),
                Decimal("12.00"),
                Decimal("8.00"),
                12,
                Product.Unit.PACK,
            ),
            # Maraîchers Cap Bon
            (
                merchant_objs["Les Maraîchers du Cap Bon"],
                cat_map["fruits-legumes"],
                "Cagette de Tomates et Piments de Saison (10 kg)",
                "Légumes frais de saison récoltés la veille dans les fermes de Nabeul.",
                Product.Kind.DONATION,
                Decimal("0.00"),
                Decimal("0.00"),
                Decimal("0.00"),
                25,
                Product.Unit.KG,
            ),
            (
                merchant_objs["Les Maraîchers du Cap Bon"],
                cat_map["fruits-legumes"],
                "Cagette d'Oranges Maltaises de Tunisie (15 kg)",
                "Oranges maltaises douces du Cap Bon pour distribution aux familles.",
                Product.Kind.DISCOUNT,
                Decimal("45.00"),
                Decimal("15.00"),
                Decimal("10.00"),
                18,
                Product.Unit.KG,
            ),
            # Épicerie Bio Sahel
            (
                merchant_objs["Épicerie Bio du Sahel"],
                cat_map["epicerie-seche"],
                "Bidons d'Huile d'Olive Vierge Extra (3 Litres)",
                "Huile d'olive du Sahel tunisien offerte pour cuisines collectives.",
                Product.Kind.DISCOUNT,
                Decimal("75.00"),
                Decimal("30.00"),
                Decimal("20.00"),
                10,
                Product.Unit.PIECE,
            ),
        ]

        prod_objs = []
        for m, cat, name, desc, kind, orig, offer, cred, stock, unit in products_data:
            p, _ = Product.objects.get_or_create(
                merchant=m,
                name=name,
                defaults={
                    "category": cat,
                    "description": desc,
                    "kind": kind,
                    "original_price": orig,
                    "offer_price": offer,
                    "credit_cost": cred,
                    "stock": stock,
                    "unit": unit,
                    "status": Product.Status.APPROVED,
                },
            )
            prod_objs.append(p)

        # 8. Beneficiaries
        beneficiaries_data = [
            ("Mabrouka", "Gharbi", "+216 97 111 222", "Cité El Khadra", "Tunis", 5, "Denrées de base, produits laitiers, lait infantile", Beneficiary.Priority.HIGH),
            ("Noureddine", "Trabelsi", "+216 96 333 444", "Bab Souika", "Tunis", 4, "Pain quotidien, farine, légumineuses", Beneficiary.Priority.MEDIUM),
            ("Chiraz", "Ben Salem", "+216 95 555 666", "Djebel Jelloud", "Tunis", 6, "Paniers de légumes, semoule, huile", Beneficiary.Priority.HIGH),
            ("Mohamed", "Kacem", "+216 94 777 888", "Cité El Habib", "Sfax", 3, "Pains, produits d'hygiène, savon", Beneficiary.Priority.LOW),
            ("Habiba", "Masmoudi", "+216 93 999 000", "Route de Téniour", "Sfax", 5, "Alimentation générale pour personnes âgées", Beneficiary.Priority.HIGH),
            ("Amine", "Sellami", "+216 92 123 456", "Cité Olympique", "Ariana", 2, "Étudiant boursier, repas et conserves", Beneficiary.Priority.MEDIUM),
        ]

        beneficiary_objs = []
        for fn, ln, ph, addr, city, hh, nds, prio in beneficiaries_data:
            # Associate first 3 with CRT, next 2 with USPT, last with INSAT
            assigned_assoc = crt if city == "Tunis" else (uspt if city == "Sfax" else assoc_objs["Club Solidarité INSAT"])
            b, _ = Beneficiary.objects.get_or_create(
                association=assigned_assoc,
                first_name=fn,
                last_name=ln,
                defaults={
                    "phone": ph,
                    "address": addr,
                    "city": city,
                    "household_size": hh,
                    "needs": nds,
                    "priority": prio,
                    "is_active": True,
                },
            )
            beneficiary_objs.append(b)

        # 9. Sample Reservations & Collections
        pickup_today = today + datetime.timedelta(days=1)
        res1, created = Reservation.objects.get_or_create(
            association=crt,
            merchant=merchant_objs["Boulangerie Artisanale Elyssa"],
            pickup_date=pickup_today,
            defaults={
                "status": Reservation.Status.ACCEPTED,
                "notes": "Collecte quotidienne pour la cantine solidaire de Tunis.",
                "credits_spent": Decimal("5.00"),
            },
        )
        if created:
            ReservationItem.objects.create(
                reservation=res1,
                product=prod_objs[0],
                quantity=3,
                unit_credit_cost=Decimal("0.00"),
                product_name=prod_objs[0].name,
            )
            ReservationItem.objects.create(
                reservation=res1,
                product=prod_objs[1],
                quantity=1,
                unit_credit_cost=Decimal("5.00"),
                product_name=prod_objs[1].name,
            )
            Collection.objects.create(
                reservation=res1,
                status=Collection.Status.SCHEDULED,
                scheduled_for=pickup_today,
                notes="Préparer les sachets pour 17h00.",
                organized_by=merchant_objs["Boulangerie Artisanale Elyssa"].user,
            )

        # Completed reservation and collection
        res2, created2 = Reservation.objects.get_or_create(
            association=crt,
            merchant=merchant_objs["Les Maraîchers du Cap Bon"],
            pickup_date=today - datetime.timedelta(days=2),
            defaults={
                "status": Reservation.Status.COLLECTED,
                "notes": "Livraison maraîchère de soutien.",
                "credits_spent": Decimal("10.00"),
            },
        )
        if created2:
            ReservationItem.objects.create(
                reservation=res2,
                product=prod_objs[5],
                quantity=2,
                unit_credit_cost=Decimal("0.00"),
                product_name=prod_objs[5].name,
            )
            Collection.objects.create(
                reservation=res2,
                status=Collection.Status.COMPLETED,
                scheduled_for=today - datetime.timedelta(days=2),
                completed_at=timezone.now() - datetime.timedelta(days=2),
                notes="Collecte effectuée par les bénévoles.",
                organized_by=merchant_objs["Les Maraîchers du Cap Bon"].user,
            )

        # 10. Sample Distributions
        Distribution.objects.get_or_create(
            association=crt,
            beneficiary=beneficiary_objs[0],
            title="Panier légumes frais et pain solidaire",
            defaults={
                "quantity": 1,
                "unit": "lot",
                "distributed_on": today - datetime.timedelta(days=1),
                "notes": "Remis en main propre au centre d'écoute de Cité El Khadra.",
                "recorded_by": crt.user,
            },
        )
        Distribution.objects.get_or_create(
            association=crt,
            beneficiary=beneficiary_objs[1],
            title="Lot de baguettes tradition et viennoiseries",
            defaults={
                "quantity": 4,
                "unit": "piece",
                "distributed_on": today - datetime.timedelta(days=1),
                "notes": "Distribution du matin.",
                "recorded_by": crt.user,
            },
        )

        # 11. Credit Transactions
        CreditTransaction.objects.get_or_create(
            association=crt,
            description="Initialisation du solde de bienvenue solidaire",
            defaults={
                "amount": Decimal("250.00"),
                "balance_after": Decimal("250.00"),
                "tx_type": CreditTransaction.Type.GRANT,
                "created_by": admin_user,
            },
        )

        # 12. Notifications
        Notification.objects.get_or_create(
            recipient=crt.user,
            title="Bienvenue sur Donatily !",
            defaults={
                "body": "Votre compte association est validé. Vous pouvez dès maintenant parcourir les commerçants et réserver des dons.",
                "link": "/association/products/",
                "is_read": False,
            },
        )
        Notification.objects.get_or_create(
            recipient=merchant_objs["Boulangerie Artisanale Elyssa"].user,
            title="Nouvelle réservation confirmée",
            defaults={
                "body": f"Réservation #{res1.pk} programmée pour le {pickup_today:%d/%m/%Y}.",
                "link": f"/merchant/reservations/{res1.pk}/",
                "is_read": False,
            },
        )

        # 13. Activity Logs
        ActivityLog.objects.get_or_create(
            action="platform.seed",
            entity_type="system",
            defaults={
                "actor": admin_user,
                "message": "Données initiales de démonstration initialisées.",
                "metadata": {"environment": "development"},
            },
        )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully with Tunisian solidarity data!"))
