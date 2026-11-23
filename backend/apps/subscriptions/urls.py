from django.urls import path

from .views import (
    SubscriptionActionView,
    SubscriptionDetailView,
    SubscriptionListCreateView,
)

urlpatterns = [
    path("", SubscriptionListCreateView.as_view(), name="subscription-list-create"),
    path("<int:pk>/", SubscriptionDetailView.as_view(), name="subscription-detail"),
    path("<int:pk>/action/", SubscriptionActionView.as_view(), name="subscription-action"),
]
