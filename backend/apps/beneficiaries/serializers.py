from rest_framework import serializers

from .models import Beneficiary


class BeneficiarySerializer(serializers.ModelSerializer):
    association_name = serializers.CharField(source="association.name", read_only=True)
    full_name = serializers.CharField(read_only=True)
    distributions_count = serializers.SerializerMethodField()

    class Meta:
        model = Beneficiary
        fields = [
            "id",
            "association",
            "association_name",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "address",
            "city",
            "household_size",
            "needs",
            "priority",
            "is_active",
            "notes",
            "distributions_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "association", "full_name", "distributions_count", "created_at", "updated_at"]

    def get_distributions_count(self, obj):
        return obj.distributions.count()
