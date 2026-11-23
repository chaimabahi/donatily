from rest_framework import serializers

from apps.accounts.services import absolute_media

from .models import Collection, Reservation, ReservationItem, ReservationMessage


class ReservationMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.display_name", read_only=True)
    sender_role = serializers.CharField(source="sender.role", read_only=True)
    sender_email = serializers.CharField(source="sender.email", read_only=True)

    class Meta:
        model = ReservationMessage
        fields = [
            "id",
            "reservation",
            "sender",
            "sender_name",
            "sender_role",
            "sender_email",
            "content",
            "created_at",
        ]
        read_only_fields = ["id", "reservation", "sender", "created_at"]


class ReservationItemSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = ReservationItem
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "product_image",
        ]

    def get_product_image(self, obj):
        if obj.product and obj.product.primary_image:
            return absolute_media(self.context.get("request"), obj.product.primary_image.image)
        return None


class CollectionSerializer(serializers.ModelSerializer):
    organized_by_name = serializers.CharField(source="organized_by.display_name", read_only=True)
    merchant_name = serializers.CharField(source="reservation.merchant.business_name", read_only=True)
    merchant_city = serializers.CharField(source="reservation.merchant.city", read_only=True)
    merchant_address = serializers.CharField(source="reservation.merchant.address", read_only=True)
    association_name = serializers.CharField(source="reservation.association.name", read_only=True)
    association_phone = serializers.CharField(source="reservation.association.user.phone", read_only=True)
    reservation_id = serializers.IntegerField(source="reservation.id", read_only=True)
    pickup_date = serializers.DateField(source="reservation.pickup_date", read_only=True)

    class Meta:
        model = Collection
        fields = [
            "id",
            "reservation_id",
            "merchant_name",
            "merchant_city",
            "merchant_address",
            "association_name",
            "association_phone",
            "pickup_date",
            "status",
            "scheduled_for",
            "completed_at",
            "notes",
            "organized_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "reservation_id", "completed_at", "created_at", "updated_at"]


class ReservationSerializer(serializers.ModelSerializer):
    items = ReservationItemSerializer(many=True, read_only=True)
    collection = CollectionSerializer(read_only=True)
    messages = ReservationMessageSerializer(many=True, read_only=True)
    association_name = serializers.CharField(source="association.name", read_only=True)
    association_city = serializers.CharField(source="association.city", read_only=True)
    association_phone = serializers.CharField(source="association.user.phone", read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)
    merchant_city = serializers.CharField(source="merchant.city", read_only=True)
    merchant_address = serializers.CharField(source="merchant.address", read_only=True)
    merchant_phone = serializers.CharField(source="merchant.user.phone", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "association",
            "association_name",
            "association_city",
            "association_phone",
            "merchant",
            "merchant_name",
            "merchant_city",
            "merchant_address",
            "merchant_phone",
            "status",
            "pickup_date",
            "notes",
            "rejection_reason",
            "items",
            "collection",
            "messages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "association",
            "merchant",
            "status",
            "rejection_reason",
            "items",
            "collection",
            "messages",
            "created_at",
            "updated_at",
        ]


class ItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class ReservationCreateSerializer(serializers.Serializer):
    items = ItemInputSerializer(many=True)
    pickup_date = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ReservationActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "reject", "cancel"])
    reason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class CollectionActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["complete", "miss"])
    notes = serializers.CharField(required=False, allow_blank=True)
