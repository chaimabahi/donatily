from django.urls import include, path

urlpatterns = [
    path("", include("apps.portal.urls")),
]
