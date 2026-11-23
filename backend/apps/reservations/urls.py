from django.urls import path

from .views import (
    ReservationActionView,
    ReservationDetailView,
    ReservationListCreateView,
    ReservationMessagesView,
)

urlpatterns = [
    path("", ReservationListCreateView.as_view(), name="reservation-list-create"),
    path("<int:pk>/", ReservationDetailView.as_view(), name="reservation-detail"),
    path("<int:pk>/action/", ReservationActionView.as_view(), name="reservation-action"),
    path("<int:pk>/messages/", ReservationMessagesView.as_view(), name="reservation-messages"),
]
