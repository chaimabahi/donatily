from decimal import Decimal
from rest_framework import serializers

from apps.accounts.services import absolute_media
from apps.associations.serializers import AssociationSerializer
from apps.merchants.serializers import MerchantSerializer

from .models import CreditTransaction, Subscription, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)
    merchant_city = serializers.CharField(source="merchant.city", read_only=True)
    active_subscriptions_count = serializers.SerializerMethodField()
    credits = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=Decimal("0.00"))

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "merchant",
            "merchant_name",
            "merchant_city",
            "name",
            "description",
            "price",
            "credits",
            "duration_days",
            "is_active",
            "active_subscriptions_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "merchant", "active_subscriptions_count", "created_at", "updated_at"]

    def get_active_subscriptions_count(self, obj):
        return obj.subscriptions.filter(status=Subscription.Status.ACTIVE).count()

    def validate_price(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Le prix ne peut pas être négatif.")
        return value

    def validate_credits(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Le nombre de crédits ne peut pas être négatif.")
        return value


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.all(), source="plan", write_only=True
    )
    association_name = serializers.CharField(source="association.name", read_only=True)
    association_city = serializers.CharField(source="association.city", read_only=True)
    merchant_name = serializers.CharField(source="plan.merchant.business_name", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "association",
            "association_name",
            "association_city",
            "merchant_name",
            "plan",
            "plan_id",
            "status",
            "start_date",
            "end_date",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "association",
            "status",
            "start_date",
            "end_date",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class SubscriptionActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "reject", "cancel"])
    reason = serializers.CharField(required=False, allow_blank=True)


class CreditTransactionSerializer(serializers.ModelSerializer):
    association_name = serializers.CharField(source="association.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True)

    class Meta:
        model = CreditTransaction
        fields = [
            "id",
            "association",
            "association_name",
            "amount",
            "balance_after",
            "tx_type",
            "description",
            "subscription",
            "reservation",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "association",
            "amount",
            "balance_after",
            "tx_type",
            "description",
            "subscription",
            "reservation",
            "created_by",
            "created_at",
        ]


class CreditAdjustmentSerializer(serializers.Serializer):
    association_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    tx_type = serializers.ChoiceField(choices=[CreditTransaction.Type.GRANT, CreditTransaction.Type.ADJUSTMENT])
    description = serializers.CharField(max_length=255)
