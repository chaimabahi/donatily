from django.urls import path

from .views import MerchantDetailView, MerchantListView, MerchantMeView

urlpatterns = [
    path("me/", MerchantMeView.as_view(), name="merchant-me"),
    path("", MerchantListView.as_view(), name="merchant-list"),
    path("<int:pk>/", MerchantDetailView.as_view(), name="merchant-detail"),
]
