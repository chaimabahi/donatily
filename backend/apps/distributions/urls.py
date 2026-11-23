from django.urls import path

from .views import DistributionDetailView, DistributionListCreateView

urlpatterns = [
    path("", DistributionListCreateView.as_view(), name="distribution-list-create"),
    path("<int:pk>/", DistributionDetailView.as_view(), name="distribution-detail"),
]
