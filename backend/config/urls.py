from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.accounts.views import HealthView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", HealthView.as_view(), name="health"),
    path("api/health/", HealthView.as_view(), name="api-health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/associations/", include("apps.associations.urls")),
    path("api/merchants/", include("apps.merchants.urls")),
    path("api/categories/", include("apps.products.category_urls")),
    path("api/products/", include("apps.products.urls")),
    path("api/plans/", include("apps.subscriptions.plan_urls")),
    path("api/subscriptions/", include("apps.subscriptions.urls")),
    path("api/credits/", include("apps.subscriptions.credit_urls")),
    path("api/reservations/", include("apps.reservations.urls")),
    path("api/collections/", include("apps.reservations.collection_urls")),
    path("api/beneficiaries/", include("apps.beneficiaries.urls")),
    path("api/distributions/", include("apps.distributions.urls")),
    path("api/notifications/", include("apps.accounts.notification_urls")),
    path("api/activity/", include("apps.accounts.activity_urls")),
    path("api/stats/", include("apps.accounts.stats_urls")),
]

if settings.DEBUG and not settings.USE_S3:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Donatily administration"
admin.site.site_title = "Donatily"
admin.site.index_title = "Pilotage de la plateforme"
