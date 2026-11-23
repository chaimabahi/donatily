from django.urls import path

from .views import CollectionActionView, CollectionDetailView, CollectionListView

urlpatterns = [
    path("", CollectionListView.as_view(), name="collection-list"),
    path("<int:pk>/", CollectionDetailView.as_view(), name="collection-detail"),
    path("<int:pk>/action/", CollectionActionView.as_view(), name="collection-action"),
]
