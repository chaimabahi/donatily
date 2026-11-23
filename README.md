# DONATILY — Plateforme Tunisienne de Solidarité & Économie Circulaire

**Donatily** est une plateforme web moderne et éco-responsable connectant les associations caritatives, les clubs solidaires et les entreprises / commerçants partenaires en Tunisie pour lutter contre le gaspillage alimentaire et venir en aide aux familles vulnérables.

---

## 1. Architecture Globale

Le projet est conçu selon une architecture découplée à deux tiers indépendants :
- **Backend (`backend/`)** : Projet Django + Django REST Framework + SimpleJWT + PostgreSQL. Expose des APIs REST sécurisées avec documentation interactive OpenAPI / Swagger.
- **Frontend (`frontend/`)** : Projet Django indépendant avec Django Templates, Bootstrap 5, HTML5/CSS3, JavaScript et Chart.js. Communique exclusivement avec le backend via les APIs REST HTTP.

```text
DONATILY/
├── backend/                  # API REST Django
│   ├── config/               # Settings, URLs, WSGI, ASGI
│   ├── apps/
│   │   ├── accounts/         # User personnalisé, JWT, Notifs, Activity Logs, Stats
│   │   ├── associations/     # Profils associations & clubs solidaires
│   │   ├── merchants/        # Profils commerçants & entreprises partenaires
│   │   ├── products/         # Produits, catégories, dons, invendus, photos
│   │   ├── subscriptions/    # Formules solidaires, abonnements, crédits
│   │   ├── reservations/     # Réservations, articles, collectes en magasin
│   │   ├── beneficiaries/    # Fiches bénéficiaires & gestion des besoins
│   │   └── distributions/    # Distributions effectives aux familles
│   ├── manage.py
│   ├── requirements.txt
│   └── verify_apis.py
│
├── frontend/                 # Portail Web Django Templates + Bootstrap 5
│   ├── config/               # Settings frontend, URLs, WSGI
│   ├── apps/
│   │   └── portal/           # Client API REST, middleware de rôles, vues
│   │       ├── api_client.py # Client HTTP avec gestion de token JWT
│   │       ├── middleware.py # Sécurité par rôle (Association, Commerçant, Admin)
│   │       └── views/        # Vues Auth, Public, Association, Commerçant, Admin
│   ├── templates/            # Templates HTML Bootstrap 5 réutilisables
│   │   ├── base.html
│   │   ├── components/       # Navbar, sidebar, footer, messages
│   │   ├── public/           # Landing page, catalogue public, annuaire commerces
│   │   ├── auth/             # Login, inscription association, inscription commerçant
│   │   ├── association/      # Dashboard, dons, réservations, collectes, bénéficiaires...
│   │   ├── merchant/         # Dashboard, gestion stocks, formules, collectes...
│   │   └── admin_portal/     # Dashboard global, modération, validation comptes...
│   ├── static/               # CSS personnalisé & scripts Chart.js
│   ├── manage.py
│   └── requirements.txt
│
├── README.md
└── .gitignore
```

---

## 2. Pile Technologique

- **Backend** : Python 3.13+, Django 5.2, Django REST Framework, djangorestframework-simplejwt, drf-spectacular (OpenAPI/Swagger), django-cors-headers, psycopg 3 (PostgreSQL).
- **Frontend** : Django 5.2, Django Templates, HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, Chart.js, Requests.
- **Base de données** : PostgreSQL 15+ (Local ou Amazon RDS).
- **Stockage Médias** : Amazon S3 (compatible django-storages / boto3) ou stockage local en développement.
- **Serveur d'application** : Gunicorn pour la production.

---

## 3. Modèles de Données & Relations

Les 14 modèles requis sont rigoureusement implémentés avec contraintes d'intégrité, indexations et transactions atomiques :

1. `User` : Modèle utilisateur personnalisé avec rôles (`association`, `merchant`, `admin`), email comme identifiant unique, et statut de vérification.
2. `Association` : Nom, matricule officiel JORT, ville, solde de crédits solidaires (`credit_balance >= 0`), logo, statut (`pending`, `approved`, `rejected`, `suspended`).
3. `Merchant` : Raison sociale, matricule fiscal unique, ville, adresse, horaires d'ouverture, logo, statut.
4. `Category` : Catégories de denrées (Boulangerie, Maraîchage, Produits frais, Épicerie, etc.) avec slug automatique.
5. `Product` : Produits et dons (`donation`, `unsold`, `discount`), prix d'origine, prix solidaire, coût en crédits, stock non-négatif, statut de modération (`pending`, `approved`, `rejected`).
6. `ProductImage` : Images multiples par produit avec gestion de photo principale.
7. `SubscriptionPlan` : Formules solidaires créées par les commerçants (prix en TND, crédits mensuels, durée en jours).
8. `Subscription` : Souscriptions des associations aux formules des commerçants (`pending`, `active`, `rejected`, `cancelled`, `expired`).
9. `CreditTransaction` : Journal comptable des crédits (`grant`, `debit`, `refund`, `adjustment`) avec calcul automatique du solde après opération.
10. `Reservation` : Réservations de produits par les associations avec contrôle atomique de stock et débit de crédits.
11. `ReservationItem` : Lignes d'articles d'une réservation (quantité, coût unitaire, nom figé).
12. `Collection` : Collecte physique planifiée en magasin (`scheduled`, `completed`, `missed`, `cancelled`).
13. `Beneficiary` : Personnes et familles recensées par l'association (foyer, besoins spécifiques, niveau d'urgence `high`, `medium`, `low`).
14. `Distribution` : Enregistrement des remises de denrées aux bénéficiaires pour traçabilité complète.
15. `Notification` & `ActivityLog` : Notifications in-app et journal d'audit des actions plateforme.

---

## 4. Comptes de Démonstration (Tunisie)

Après l'exécution de la commande de seed, les comptes suivants sont prêts à l'emploi :

| Rôle | Adresse e-mail | Mot de passe | Description |
| :--- | :--- | :--- | :--- |
| **Administrateur** | `admin@donatily.tn` | `AdminPass123!` | Super-administrateur plateforme |
| **Association** | `croissant.rouge@tunisie.tn` | `AssocPass123!` | Croissant-Rouge Tunisien (Section Tunis) |
| **Association** | `un_sourire_tous@gmail.com` | `AssocPass123!` | Un Sourire Pour Tous (Sfax) |
| **Commerçant** | `contact@boulangerie-elyssa.tn` | `MerchantPass123!` | Boulangerie Artisanale Elyssa (Tunis) |
| **Commerçant** | `maraicher.capbon@topnet.tn` | `MerchantPass123!` | Les Maraîchers du Cap Bon (Nabeul) |

---

## 5. Guide d'Installation et Exécution Locale

### Prérequis
- Python 3.11+
- PostgreSQL en cours d'exécution sur `127.0.0.1:5432` avec la base `donatily` et l'utilisateur `donatily` (mot de passe: `donatily`).

### Étape 1 : Initialisation du Backend
```bash
# Aller dans le backend
cd backend

# Copier le fichier d'environnement
cp .env.example .env

# Installer les dépendances
pip install -r requirements.txt

# Appliquer les migrations PostgreSQL
python manage.py migrate

# Peupler la base avec les données tunisiennes de test
python manage.py seed_demo_data

# Vérifier les endpoints et l'intégrité
python verify_apis.py

# Démarrer le serveur API Backend sur le port 8001
python manage.py runserver 127.0.0.1:8001
```

Accès Backend :
- Swagger / OpenAPI UI : [http://127.0.0.1:8001/api/docs/](http://127.0.0.1:8001/api/docs/)
- Django Admin : [http://127.0.0.1:8001/admin/](http://127.0.0.1:8001/admin/)
- Endpoint Healthcheck : [http://127.0.0.1:8001/api/health/](http://127.0.0.1:8001/api/health/)

---

### Étape 2 : Initialisation du Frontend
Dans un second terminal :
```bash
# Aller dans le frontend
cd frontend

# Copier le fichier d'environnement
cp .env.example .env

# Installer les dépendances
pip install -r requirements.txt

# Initialiser la base de session locale
python manage.py migrate

# Démarrer le serveur Frontend sur le port 8000
python manage.py runserver 127.0.0.1:8000
```

Accès Frontend :
- Portail web public : [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Page de connexion : [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
- Catalogue des dons : [http://127.0.0.1:8000/explore/products/](http://127.0.0.1:8000/explore/products/)
- Annuaire commerces : [http://127.0.0.1:8000/explore/merchants/](http://127.0.0.1:8000/explore/merchants/)

---

## 6. Compatibilité Déploiement AWS

L'application est 100% prête pour le déploiement sur votre infrastructure AWS existante :

### Backend sur EC2 (Auto Scaling + ALB privé)
- Variables d'environnement à injecter :
  - `DB_ENGINE=postgresql`
  - `DB_HOST=<endpoint-rds-postgresql>`
  - `DB_NAME=donatily`
  - `DB_USER=donatily`
  - `DB_PASSWORD=<votre-mot-de-passe>`
  - `USE_S3=True`
  - `AWS_STORAGE_BUCKET_NAME=<nom-du-bucket-s3>`
  - `AWS_S3_REGION_NAME=eu-west-3`
  - `SECRET_KEY=<cle-de-production>`
  - `ALLOWED_HOSTS=<dns-du-load-balancer>,api.donatily.tn`

- Commande de démarrage Gunicorn (Backend) :
  ```bash
  gunicorn config.wsgi:application --bind 0.0.0.0:8001 --workers 4 --threads 2 --timeout 60
  ```

### Frontend sur EC2 (Auto Scaling + ALB public)
- Variables d'environnement à injecter :
  - `BACKEND_API_URL=http://<dns-interne-alb-backend>:8001` (ou `https://api.donatily.tn`)
  - `SECRET_KEY=<cle-frontend-production>`
  - `ALLOWED_HOSTS=<dns-du-load-balancer-public>,donatily.tn,www.donatily.tn`

- Commande de démarrage Gunicorn (Frontend) :
  ```bash
  gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2 --timeout 60
  ```

---

## 7. Tests & Validation

Un script complet de validation des scénarios réels est inclus et validé :
```bash
python backend/test_donatily_e2e.py
```
Il vérifie :
- Authentification JWT pour les 3 rôles.
- Publication d'offres par le commerçant.
- Modération et approbation par l'administrateur.
- Débit de crédits atomique et réservation de stock par l'association.
- Acceptation et planification de collecte.
- Confirmation de collecte physique.
- Recensement de bénéficiaire et distribution effective.
