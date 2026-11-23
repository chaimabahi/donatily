from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed

from apps.associations.models import Association
from apps.merchants.models import Merchant

from .models import ActivityLog, Notification, User
from .services import absolute_media


def ensure_password(password, user=None):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "is_verified",
            "is_active",
            "display_name",
            "profile",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "email", "role", "is_verified", "is_active", "date_joined", "last_login"]

    def get_profile(self, obj):
        request = self.context.get("request")
        if obj.role == User.Role.ASSOCIATION:
            try:
                association = obj.association_profile
            except Association.DoesNotExist:
                return None
            return {
                "id": association.id,
                "name": association.name,
                "status": association.status,
                "city": association.city,
                "registration_number": association.registration_number,
                "logo": absolute_media(request, association.logo),
            }
        if obj.role == User.Role.MERCHANT:
            try:
                merchant = obj.merchant_profile
            except Merchant.DoesNotExist:
                return None
            return {
                "id": merchant.id,
                "name": merchant.business_name,
                "status": merchant.status,
                "city": merchant.city,
                "tax_id": merchant.tax_id,
                "logo": absolute_media(request, merchant.logo),
            }
        return None


class DonatilyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)
        except AuthenticationFailed as exc:
            email = attrs.get("email") or attrs.get("username") or ""
            user = User.objects.filter(email__iexact=email).first()
            if user and not user.is_active and user.check_password(attrs.get("password", "")):
                raise AuthenticationFailed("Ce compte est suspendu.") from exc
            raise AuthenticationFailed("E-mail ou mot de passe incorrect.") from exc
        data["user"] = UserSerializer(self.user, context=self.context).data
        return data


class AssociationRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    name = serializers.CharField(max_length=180)
    description = serializers.CharField(required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=80)
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=120)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet e-mail.")
        return value.lower()

    def validate_password(self, value):
        ensure_password(value)
        return value

    def validate_registration_number(self, value):
        if Association.objects.filter(registration_number__iexact=value).exists():
            raise serializers.ValidationError("Ce numéro d'enregistrement est déjà utilisé.")
        return value.strip()

    def create(self, validated_data):
        password = validated_data.pop("password")
        profile_fields = {
            key: validated_data.pop(key)
            for key in ["name", "description", "registration_number", "address", "city", "postal_code", "website"]
            if key in validated_data
        }
        with transaction.atomic():
            user = User.objects.create_user(password=password, role=User.Role.ASSOCIATION, is_verified=True, **validated_data)
            Association.objects.create(user=user, status=Association.Status.APPROVED, **profile_fields)
        return user


class MerchantRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    business_name = serializers.CharField(max_length=180)
    description = serializers.CharField(required=False, allow_blank=True)
    tax_id = serializers.CharField(max_length=80)
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=120)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    opening_hours = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet e-mail.")
        return value.lower()

    def validate_password(self, value):
        ensure_password(value)
        return value

    def validate_tax_id(self, value):
        if Merchant.objects.filter(tax_id__iexact=value).exists():
            raise serializers.ValidationError("Ce matricule fiscal est déjà utilisé.")
        return value.strip()

    def create(self, validated_data):
        password = validated_data.pop("password")
        profile_keys = ["business_name", "description", "tax_id", "address", "city", "postal_code", "website", "opening_hours"]
        profile_fields = {key: validated_data.pop(key) for key in profile_keys if key in validated_data}
        with transaction.atomic():
            user = User.objects.create_user(password=password, role=User.Role.MERCHANT, is_verified=True, **validated_data)
            Merchant.objects.create(user=user, status=Merchant.Status.APPROVED, **profile_fields)
        return user


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "Mot de passe actuel incorrect."})
        ensure_password(attrs["new_password"], user=user)
        return attrs


class AccountReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "suspend", "reactivate"])
    reason = serializers.CharField(required=False, allow_blank=True)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "link", "is_read", "created_at", "read_at"]


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = ActivityLog
        fields = ["id", "actor", "actor_email", "action", "entity_type", "entity_id", "message", "metadata", "created_at"]
