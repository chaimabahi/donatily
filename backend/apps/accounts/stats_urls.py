from django.urls import path

from .stats import AdminStatsView, AssociationStatsView, MerchantStatsView

urlpatterns = [
    path("association/", AssociationStatsView.as_view(), name="stats-association"),
    path("merchant/", MerchantStatsView.as_view(), name="stats-merchant"),
    path("admin/", AdminStatsView.as_view(), name="stats-admin"),
]
