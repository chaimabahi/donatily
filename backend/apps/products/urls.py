from django.urls import path

from .views import (
    ProductDetailView,
    ProductImageDeleteView,
    ProductImageUploadView,
    ProductListCreateView,
    ProductModerateView,
)

urlpatterns = [
    path("", ProductListCreateView.as_view(), name="product-list-create"),
    path("<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("<int:pk>/images/", ProductImageUploadView.as_view(), name="product-image-upload"),
    path("<int:pk>/moderate/", ProductModerateView.as_view(), name="product-moderate"),
    path("images/<int:pk>/", ProductImageDeleteView.as_view(), name="product-image-delete"),
]
