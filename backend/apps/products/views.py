from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.pagination import DefaultPagination
from apps.accounts.permissions import IsAdmin, IsMerchant
from apps.accounts.services import log_activity, notify

from .models import Category, Product, ProductImage
from .serializers import (
    CategorySerializer,
    ModerationSerializer,
    ProductImageSerializer,
    ProductImageUploadSerializer,
    ProductSerializer,
)


class CategoryListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdmin()]

    def get(self, request):
        categories = Category.objects.all().order_by("name")
        query = request.query_params.get("q")
        if query:
            categories = categories.filter(name__icontains=query)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        log_activity(request.user, "category.create", "category", category.pk, f"Catégorie {category.name} créée.")
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdmin()]

    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        return Response(CategorySerializer(category).data)

    def patch(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_activity(request.user, "category.update", "category", category.pk, f"Catégorie {category.name} modifiée.")
        return Response(serializer.data)

    def delete(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        if category.products.exists():
            raise ValidationError({"detail": "Impossible de supprimer une catégorie liée à des produits."})
        name = category.name
        category.delete()
        log_activity(request.user, "category.delete", "category", pk, f"Catégorie {name} supprimée.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsMerchant()]

    def get(self, request):
        queryset = (
            Product.objects.select_related("merchant", "category")
            .prefetch_related("images")
            .all()
        )

        user = request.user
        is_admin = user.is_authenticated and user.role == "admin"
        is_merchant = user.is_authenticated and user.role == "merchant"

        # Non-admins and non-merchants (or public) only see approved products with positive stock by default
        merchant_filter = request.query_params.get("merchant")
        status_param = request.query_params.get("status")

        if is_admin:
            if status_param:
                queryset = queryset.filter(status=status_param)
        elif is_merchant:
            # If requesting own products
            if request.query_params.get("mine") == "true" or (
                merchant_filter and str(user.merchant_profile.id) == str(merchant_filter)
            ):
                queryset = queryset.filter(merchant=user.merchant_profile)
                if status_param:
                    queryset = queryset.filter(status=status_param)
            else:
                queryset = queryset.filter(status=Product.Status.APPROVED, stock__gt=0)
        else:
            queryset = queryset.filter(status=Product.Status.APPROVED, stock__gt=0)

        # Filters
        if merchant_filter and (not is_merchant or request.query_params.get("mine") != "true"):
            queryset = queryset.filter(merchant_id=merchant_filter)

        category_id = request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        kind = request.query_params.get("kind")
        if kind:
            queryset = queryset.filter(kind=kind)

        city = request.query_params.get("city")
        if city:
            queryset = queryset.filter(merchant__city__iexact=city)

        query = request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(merchant__business_name__icontains=query)
                | Q(category__name__icontains=query)
            )

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ProductSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        merchant = request.user.merchant_profile
        if merchant.status != "approved" or not request.user.is_verified:
            raise PermissionDenied("Votre compte commerçant doit être validé pour publier des produits.")

        serializer = ProductSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        # Newly created products start in pending moderation (or approved if auto-approved)
        product = serializer.save(merchant=merchant, status=Product.Status.PENDING)

        log_activity(
            request.user,
            "product.create",
            "product",
            product.pk,
            f"Offre {product.name} ({product.get_kind_display()}) soumise pour modération.",
        )
        return Response(
            ProductSerializer(product, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ProductDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_object(self, pk, user):
        product = get_object_or_404(
            Product.objects.select_related("merchant", "category").prefetch_related("images"),
            pk=pk,
        )
        if product.status != Product.Status.APPROVED:
            is_owner = user.is_authenticated and user.role == "merchant" and product.merchant_id == getattr(user, "merchant_profile", None) and user.merchant_profile.id == product.merchant_id
            is_admin = user.is_authenticated and user.role == "admin"
            if not is_owner and not is_admin:
                raise PermissionDenied("Ce produit n'est pas accessible.")
        return product

    def get(self, request, pk):
        product = self.get_object(pk, request.user)
        return Response(ProductSerializer(product, context={"request": request}).data)

    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        user = request.user
        is_owner = user.role == "merchant" and hasattr(user, "merchant_profile") and product.merchant_id == user.merchant_profile.id
        if user.role != "admin" and not is_owner:
            raise PermissionDenied("Vous n'êtes pas autorisé à modifier ce produit.")

        serializer = ProductSerializer(product, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        updated_product = serializer.save()

        # If modified by merchant, set back to pending moderation
        if user.role == "merchant":
            updated_product.status = Product.Status.PENDING
            updated_product.save(update_fields=["status"])

        log_activity(user, "product.update", "product", product.pk, f"Produit {product.name} mis à jour.")
        return Response(ProductSerializer(updated_product, context={"request": request}).data)

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        user = request.user
        is_owner = user.role == "merchant" and hasattr(user, "merchant_profile") and product.merchant_id == user.merchant_profile.id
        if user.role != "admin" and not is_owner:
            raise PermissionDenied("Vous n'êtes pas autorisé à supprimer ce produit.")

        name = product.name
        product.delete()
        log_activity(user, "product.delete", "product", pk, f"Produit {name} supprimé.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImageUploadView(APIView):
    permission_classes = [IsMerchant]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        merchant = request.user.merchant_profile
        if product.merchant_id != merchant.id and request.user.role != "admin":
            raise PermissionDenied("Action interdite sur ce produit.")

        serializer = ProductImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_primary = serializer.validated_data.get("is_primary", False)
        if is_primary:
            product.images.update(is_primary=False)

        img = ProductImage.objects.create(
            product=product,
            image=serializer.validated_data["image"],
            alt_text=serializer.validated_data.get("alt_text", product.name),
            is_primary=is_primary or (not product.images.exists()),
        )

        return Response(ProductImageSerializer(img, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ProductImageDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        img = get_object_or_404(ProductImage.objects.select_related("product"), pk=pk)
        user = request.user
        is_owner = user.role == "merchant" and hasattr(user, "merchant_profile") and img.product.merchant_id == user.merchant_profile.id
        if user.role != "admin" and not is_owner:
            raise PermissionDenied("Action interdite.")

        product = img.product
        was_primary = img.is_primary
        img.delete()

        if was_primary:
            first_remaining = product.images.first()
            if first_remaining:
                first_remaining.is_primary = True
                first_remaining.save(update_fields=["is_primary"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductModerateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        product = get_object_or_404(Product.objects.select_related("merchant__user"), pk=pk)
        serializer = ModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")

        if action == "approve":
            product.status = Product.Status.APPROVED
            product.moderation_note = ""
            product.save(update_fields=["status", "moderation_note", "updated_at"])
            notify(
                product.merchant.user,
                "Offre approuvée",
                f"Votre offre « {product.name} » a été approuvée et est désormais visible par les associations.",
                f"/merchant/products/{product.pk}/",
            )
            log_activity(request.user, "product.approve", "product", product.pk, f"Offre {product.name} approuvée.")
        else:
            product.status = Product.Status.REJECTED
            product.moderation_note = reason
            product.save(update_fields=["status", "moderation_note", "updated_at"])
            notify(
                product.merchant.user,
                "Offre refusée",
                f"Votre offre « {product.name} » a été refusée: {reason}",
                f"/merchant/products/{product.pk}/",
            )
            log_activity(request.user, "product.reject", "product", product.pk, f"Offre {product.name} refusée: {reason}")

        return Response(ProductSerializer(product, context={"request": request}).data)
