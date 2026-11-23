from rest_framework import serializers

from apps.beneficiaries.serializers import BeneficiarySerializer

from .models import Distribution


class DistributionSerializer(serializers.ModelSerializer):
    beneficiary_name = serializers.CharField(source="beneficiary.full_name", read_only=True)
    beneficiary_city = serializers.CharField(source="beneficiary.city", read_only=True)
    association_name = serializers.CharField(source="association.name", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.display_name", read_only=True)

    class Meta:
        model = Distribution
        fields = [
            "id",
            "association",
            "association_name",
            "beneficiary",
            "beneficiary_name",
            "beneficiary_city",
            "title",
            "quantity",
            "unit",
            "distributed_on",
            "notes",
            "recorded_by",
            "recorded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "association", "recorded_by", "created_at", "updated_at"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("La quantité doit être strictement positive.")
        return value
