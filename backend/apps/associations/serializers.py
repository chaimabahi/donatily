from rest_framework import serializers

from apps.accounts.services import absolute_media, validate_uploaded_image

from .models import Association


class AssociationSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = Association
        fields = [
            "id",
            "email",
            "phone",
            "name",
            "description",
            "registration_number",
            "address",
            "city",
            "postal_code",
            "website",
            "logo",
            "logo_url",
            "status",
            "rejection_reason",
            "credit_balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "phone",
            "status",
            "rejection_reason",
            "credit_balance",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"logo": {"write_only": True, "required": False}}

    def get_logo_url(self, obj):
        return absolute_media(self.context.get("request"), obj.logo)

    def validate_logo(self, value):
        if value:
            validate_uploaded_image(value)
        return value
