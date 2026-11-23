from django.urls import path

from .views import CreditAdjustView, CreditTransactionListView

urlpatterns = [
    path("", CreditTransactionListView.as_view(), name="credit-list"),
    path("adjust/", CreditAdjustView.as_view(), name="credit-adjust"),
]
