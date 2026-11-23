from django.urls import path

from .views import AssociationDetailView, AssociationListView, AssociationMeView

urlpatterns = [
    path("me/", AssociationMeView.as_view(), name="association-me"),
    path("", AssociationListView.as_view(), name="association-list"),
    path("<int:pk>/", AssociationDetailView.as_view(), name="association-detail"),
]
