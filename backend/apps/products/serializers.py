from decimal import Decimal

from rest_framework import serializers

from apps.accounts.services import absolute_media, validate_uploaded_image

from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary", "created_at"]

    def get_image(self, obj):
        return absolute_media(self.context.get("request"), obj.image)


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)
    merchant_city = serializers.CharField(source="merchant.city", read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "merchant",
            "merchant_name",
            "merchant_city",
            "category",
            "category_name",
            "name",
            "description",
            "kind",
            "unit",
            "original_price",
            "offer_price",
            "credit_cost",
            "stock",
            "status",
            "moderation_note",
            "expiry_date",
            "images",
            "primary_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "merchant", "status", "moderation_note", "created_at", "updated_at"]

    def get_primary_image(self, obj):
        image = obj.primary_image
        if image is None:
            return None
        return absolute_media(self.context.get("request"), image.image)

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        original = Decimal(attrs.get("original_price", getattr(self.instance, "original_price", 0)))
        offer = Decimal(attrs.get("offer_price", getattr(self.instance, "offer_price", 0)))
        credit = Decimal(attrs.get("credit_cost", getattr(self.instance, "credit_cost", 0)))
        if kind == Product.Kind.DONATION:
            attrs["original_price"] = Decimal("0.00")
            attrs["offer_price"] = Decimal("0.00")
            attrs["credit_cost"] = Decimal("0.00")
        elif kind == Product.Kind.DISCOUNT:
            if original <= 0 or offer <= 0 or offer >= original:
                raise serializers.ValidationError(
                    {"offer_price": "Le prix solidaire doit être supérieur à 0 et inférieur au prix d'origine."}
                )
            if credit <= 0:
                raise serializers.ValidationError({"credit_cost": "Une promotion solidaire a un coût en crédits."})
        elif kind == Product.Kind.UNSOLD:
            if original <= 0:
                raise serializers.ValidationError({"original_price": "Indiquez le prix de référence de l'invendu."})
            if credit < 0:
                raise serializers.ValidationError({"credit_cost": "Le coût en crédits ne peut pas être négatif."})
        return attrs


class ProductImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    alt_text = serializers.CharField(required=False, allow_blank=True)
    is_primary = serializers.BooleanField(required=False, default=False)

    def validate_image(self, value):
        validate_uploaded_image(value)
        return value


class ModerationSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True)
