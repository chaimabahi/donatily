from django.urls import path

from .views import BeneficiaryDetailView, BeneficiaryListCreateView

urlpatterns = [
    path("", BeneficiaryListCreateView.as_view(), name="beneficiary-list-create"),
    path("<int:pk>/", BeneficiaryDetailView.as_view(), name="beneficiary-detail"),
]
