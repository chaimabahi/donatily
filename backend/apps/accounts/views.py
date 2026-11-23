from django.db import connection
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import ActivityLog, Notification, User
from .pagination import DefaultPagination
from .permissions import IsAdmin
from .serializers import (
    AccountReviewSerializer,
    ActivityLogSerializer,
    AssociationRegisterSerializer,
    DonatilyTokenObtainPairSerializer,
    MerchantRegisterSerializer,
    NotificationSerializer,
    PasswordChangeSerializer,
    UserSerializer,
)
from .services import log_activity, mark_read, review_account


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            return Response({"status": "error"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "ok"})


def token_payload(user, request):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user, context={"request": request}).data,
    }


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = DonatilyTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class LogoutView(APIView):
    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterAssociationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = AssociationRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_activity(user, "account.register", "user", user.pk, f"Inscription association {user.email}.")
        return Response(token_payload(user, request), status=status.HTTP_201_CREATED)


class RegisterMerchantView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = MerchantRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_activity(user, "account.register", "user", user.pk, f"Inscription commerçant {user.email}.")
        return Response(token_payload(user, request), status=status.HTTP_201_CREATED)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PasswordChangeView(APIView):
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        log_activity(request.user, "account.password", "user", request.user.pk, "Mot de passe modifié.")
        return Response(token_payload(request.user, request))


class AdminUserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = User.objects.select_related("association_profile", "merchant_profile").order_by("-date_joined")
        role = request.query_params.get("role")
        account_status = request.query_params.get("status")
        query = request.query_params.get("q")
        if role:
            queryset = queryset.filter(role=role)
        if account_status:
            queryset = queryset.filter(
                Q(association_profile__status=account_status) | Q(merchant_profile__status=account_status)
            )
        if query:
            queryset = queryset.filter(
                Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(association_profile__name__icontains=query)
                | Q(merchant_profile__business_name__icontains=query)
            )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(UserSerializer(page, many=True, context={"request": request}).data)


class AdminUserDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_user(self, pk):
        try:
            return User.objects.select_related("association_profile", "merchant_profile").get(pk=pk)
        except User.DoesNotExist as exc:
            raise NotFound("Utilisateur introuvable.") from exc

    def get(self, request, pk):
        return Response(UserSerializer(self.get_user(pk), context={"request": request}).data)

    def post(self, request, pk):
        serializer = AccountReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = review_account(user_id=pk, actor=request.user, **serializer.validated_data)
        user = self.get_user(user.pk)
        return Response(UserSerializer(user, context={"request": request}).data)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = request.user.notifications.all()
        if request.query_params.get("unread") == "1":
            queryset = queryset.filter(is_read=False)
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(NotificationSerializer(page, many=True).data)


class NotificationReadView(APIView):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, recipient=request.user).first()
        if notification is None:
            raise NotFound("Notification introuvable.")
        mark_read(notification)
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    def post(self, request):
        from django.utils import timezone

        request.user.notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({"status": "ok"})


class UnreadCountView(APIView):
    def get(self, request):
        return Response({"unread": request.user.notifications.filter(is_read=False).count()})


class ActivityListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = ActivityLog.objects.select_related("actor")
        action = request.query_params.get("action")
        entity = request.query_params.get("entity_type")
        if action:
            queryset = queryset.filter(action=action)
        if entity:
            queryset = queryset.filter(entity_type=entity)
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ActivityLogSerializer(page, many=True).data)
