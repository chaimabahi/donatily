from decimal import Decimal
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.pagination import DefaultPagination
from apps.accounts.permissions import IsAdmin, IsAssociation, IsMerchant
from apps.accounts.services import log_activity
from apps.associations.models import Association

from .models import CreditTransaction, Subscription, SubscriptionPlan
from .serializers import (
    CreditAdjustmentSerializer,
    CreditTransactionSerializer,
    SubscriptionActionSerializer,
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
)
from .services import (
    accept_subscription,
    apply_credit,
    cancel_subscription,
    expire_due_subscriptions,
    reject_subscription,
    request_subscription,
)


class PlanListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsMerchant()]

    def get(self, request):
        queryset = SubscriptionPlan.objects.select_related("merchant").order_by("price")
        user = request.user

        # Filtering
        merchant_id = request.query_params.get("merchant")
        if merchant_id:
            queryset = queryset.filter(merchant_id=merchant_id)

        mine = request.query_params.get("mine")
        if mine == "true" and user.is_authenticated and user.role == "merchant":
            queryset = queryset.filter(merchant=user.merchant_profile)
        elif not (user.is_authenticated and user.role == "admin"):
            queryset = queryset.filter(is_active=True, merchant__status="approved")

        query = request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(merchant__business_name__icontains=query)
            )

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = SubscriptionPlanSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        merchant = request.user.merchant_profile
        if merchant.status != "approved" or not request.user.is_verified:
            raise PermissionDenied("Votre compte commerçant doit être validé pour créer des formules d'abonnement.")

        serializer = SubscriptionPlanSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        plan = serializer.save(merchant=merchant)

        log_activity(request.user, "plan.create", "subscription_plan", plan.pk, f"Formule « {plan.name} » créée.")
        return Response(SubscriptionPlanSerializer(plan, context={"request": request}).data, status=status.HTTP_201_CREATED)


class PlanDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan.objects.select_related("merchant"), pk=pk)
        return Response(SubscriptionPlanSerializer(plan, context={"request": request}).data)

    def patch(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        user = request.user
        is_owner = user.role == "merchant" and hasattr(user, "merchant_profile") and plan.merchant_id == user.merchant_profile.id
        if user.role != "admin" and not is_owner:
            raise PermissionDenied("Action interdite.")

        serializer = SubscriptionPlanSerializer(plan, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        log_activity(user, "plan.update", "subscription_plan", plan.pk, f"Formule « {plan.name} » mise à jour.")
        return Response(SubscriptionPlanSerializer(updated, context={"request": request}).data)

    def delete(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        user = request.user
        is_owner = user.role == "merchant" and hasattr(user, "merchant_profile") and plan.merchant_id == user.merchant_profile.id
        if user.role != "admin" and not is_owner:
            raise PermissionDenied("Action interdite.")

        # Deactivate instead of hard delete if subscriptions exist
        if plan.subscriptions.exists():
            plan.is_active = False
            plan.save(update_fields=["is_active"])
            log_activity(user, "plan.deactivate", "subscription_plan", pk, f"Formule « {plan.name} » désactivée.")
            return Response({"detail": "Formule désactivée car des abonnements y sont rattachés."}, status=status.HTTP_200_OK)

        name = plan.name
        plan.delete()
        log_activity(user, "plan.delete", "subscription_plan", pk, f"Formule « {name} » supprimée.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        expire_due_subscriptions()
        user = request.user
        queryset = Subscription.objects.select_related(
            "association", "association__user", "plan", "plan__merchant", "plan__merchant__user"
        ).order_by("-created_at")

        if user.role == "association":
            queryset = queryset.filter(association=user.association_profile)
        elif user.role == "merchant":
            queryset = queryset.filter(plan__merchant=user.merchant_profile)
        elif user.role != "admin":
            return Response([])

        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = SubscriptionSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role != "association":
            raise PermissionDenied("Seules les associations peuvent souscrire un abonnement solidaire.")

        plan_id = request.data.get("plan_id")
        if not plan_id:
            raise ValidationError({"plan_id": "L'identifiant de la formule est obligatoire."})

        plan = get_object_or_404(SubscriptionPlan.objects.select_related("merchant__user"), pk=plan_id)
        subscription = request_subscription(
            association=request.user.association_profile,
            plan=plan,
            actor=request.user,
        )
        return Response(SubscriptionSerializer(subscription, context={"request": request}).data, status=status.HTTP_201_CREATED)


class SubscriptionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        expire_due_subscriptions()
        subscription = get_object_or_404(
            Subscription.objects.select_related("association", "plan", "plan__merchant"),
            pk=pk,
        )
        user = request.user
        is_assoc = user.role == "association" and hasattr(user, "association_profile") and subscription.association_id == user.association_profile.id
        is_merch = user.role == "merchant" and hasattr(user, "merchant_profile") and subscription.plan.merchant_id == user.merchant_profile.id
        if user.role != "admin" and not is_assoc and not is_merch:
            raise PermissionDenied("Vous n'avez pas accès à cet abonnement.")

        return Response(SubscriptionSerializer(subscription, context={"request": request}).data)


class SubscriptionActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = SubscriptionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")

        if action == "accept":
            sub = accept_subscription(subscription_id=pk, actor=request.user)
        elif action == "reject":
            sub = reject_subscription(subscription_id=pk, actor=request.user, reason=reason)
        elif action == "cancel":
            sub = cancel_subscription(subscription_id=pk, actor=request.user)
        else:
            raise ValidationError({"action": "Action inconnue."})

        return Response(SubscriptionSerializer(sub, context={"request": request}).data)


class CreditTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = CreditTransaction.objects.select_related("association", "created_by").order_by("-created_at")

        if user.role == "association":
            queryset = queryset.filter(association=user.association_profile)
        elif user.role == "admin":
            assoc_id = request.query_params.get("association")
            if assoc_id:
                queryset = queryset.filter(association_id=assoc_id)
        else:
            raise PermissionDenied("Accès réservé aux associations et administrateurs.")

        tx_type = request.query_params.get("type")
        if tx_type:
            queryset = queryset.filter(tx_type=tx_type)

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = CreditTransactionSerializer(page, many=True, context={"request": request})

        balance = None
        if user.role == "association" and hasattr(user, "association_profile"):
            balance = str(user.association_profile.credit_balance)

        response = paginator.get_paginated_response(serializer.data)
        if balance is not None:
            response.data["credit_balance"] = balance
        return response


class CreditAdjustView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = CreditAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        association = get_object_or_404(Association, pk=serializer.validated_data["association_id"])
        tx = apply_credit(
            association=association,
            amount=serializer.validated_data["amount"],
            tx_type=serializer.validated_data["tx_type"],
            description=serializer.validated_data["description"],
            created_by=request.user,
        )
        log_activity(
            request.user,
            "credit.adjust",
            "association",
            association.pk,
            f"Ajustement crédit {tx.amount} pour {association.name}.",
            {"new_balance": str(association.credit_balance)},
        )
        return Response(CreditTransactionSerializer(tx, context={"request": request}).data, status=status.HTTP_201_CREATED)
