from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.pagination import DefaultPagination
from apps.accounts.permissions import IsAdmin, IsAssociation, IsMerchant

from .models import Collection, Reservation, ReservationMessage
from .serializers import (
    CollectionActionSerializer,
    CollectionSerializer,
    ReservationActionSerializer,
    ReservationCreateSerializer,
    ReservationMessageSerializer,
    ReservationSerializer,
)
from .services import (
    accept_reservation,
    cancel_reservation,
    complete_collection,
    create_reservation,
    miss_collection,
    post_reservation_message,
    reject_reservation,
)


class ReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = (
            Reservation.objects.select_related(
                "association", "association__user", "merchant", "merchant__user", "collection"
            )
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        if user.role == "association":
            queryset = queryset.filter(association=user.association_profile)
        elif user.role == "merchant":
            queryset = queryset.filter(merchant=user.merchant_profile)
        elif user.role != "admin":
            return Response([])

        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        date_from = request.query_params.get("pickup_date")
        if date_from:
            queryset = queryset.filter(pickup_date=date_from)

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ReservationSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role != "association":
            raise PermissionDenied("Seules les associations peuvent réserver des produits.")

        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reservation = create_reservation(
            association=request.user.association_profile,
            items=serializer.validated_data["items"],
            pickup_date=serializer.validated_data["pickup_date"],
            notes=serializer.validated_data.get("notes", ""),
            actor=request.user,
        )

        return Response(
            ReservationSerializer(reservation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ReservationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        reservation = get_object_or_404(
            Reservation.objects.select_related(
                "association", "association__user", "merchant", "merchant__user", "collection"
            ).prefetch_related("items__product"),
            pk=pk,
        )
        user = request.user
        is_assoc = user.role == "association" and hasattr(user, "association_profile") and reservation.association_id == user.association_profile.id
        is_merch = user.role == "merchant" and hasattr(user, "merchant_profile") and reservation.merchant_id == user.merchant_profile.id
        if user.role != "admin" and not is_assoc and not is_merch:
            raise PermissionDenied("Vous n'avez pas accès à cette réservation.")

        return Response(ReservationSerializer(reservation, context={"request": request}).data)


class ReservationActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = ReservationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")
        notes = serializer.validated_data.get("notes", "")

        if action == "accept":
            res = accept_reservation(reservation_id=pk, actor=request.user, notes=notes)
        elif action == "reject":
            res = reject_reservation(reservation_id=pk, actor=request.user, reason=reason or notes)
        elif action == "cancel":
            res = cancel_reservation(reservation_id=pk, actor=request.user, reason=reason or notes)
        else:
            raise ValidationError({"action": "Action inconnue."})

        return Response(ReservationSerializer(res, context={"request": request}).data)


class ReservationMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        reservation = get_object_or_404(
            Reservation.objects.select_related("association__user", "merchant__user"),
            pk=pk,
        )
        user = request.user
        is_assoc = user.role == "association" and hasattr(user, "association_profile") and reservation.association_id == user.association_profile.id
        is_merch = user.role == "merchant" and hasattr(user, "merchant_profile") and reservation.merchant_id == user.merchant_profile.id
        if user.role != "admin" and not is_assoc and not is_merch:
            raise PermissionDenied("Vous n'avez pas accès à cette réservation.")

        messages = reservation.messages.select_related("sender").order_by("created_at")
        return Response(ReservationMessageSerializer(messages, many=True).data)

    def post(self, request, pk):
        content = request.data.get("content", "")
        msg = post_reservation_message(
            reservation_id=pk,
            actor=request.user,
            content=content,
        )
        return Response(ReservationMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class CollectionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = Collection.objects.select_related(
            "reservation", "reservation__association", "reservation__association__user",
            "reservation__merchant", "reservation__merchant__user", "organized_by"
        ).order_by("scheduled_for", "-created_at")

        if user.role == "association":
            queryset = queryset.filter(reservation__association=user.association_profile)
        elif user.role == "merchant":
            queryset = queryset.filter(reservation__merchant=user.merchant_profile)
        elif user.role != "admin":
            return Response([])

        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = CollectionSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class CollectionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        collection = get_object_or_404(
            Collection.objects.select_related(
                "reservation", "reservation__association", "reservation__association__user",
                "reservation__merchant", "reservation__merchant__user", "organized_by"
            ),
            pk=pk,
        )
        user = request.user
        is_assoc = user.role == "association" and hasattr(user, "association_profile") and collection.reservation.association_id == user.association_profile.id
        is_merch = user.role == "merchant" and hasattr(user, "merchant_profile") and collection.reservation.merchant_id == user.merchant_profile.id
        if user.role != "admin" and not is_assoc and not is_merch:
            raise PermissionDenied("Accès interdit.")

        return Response(CollectionSerializer(collection, context={"request": request}).data)


class CollectionActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = CollectionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        notes = serializer.validated_data.get("notes", "")

        if action == "complete":
            col = complete_collection(collection_id=pk, actor=request.user, notes=notes)
        elif action == "miss":
            col = miss_collection(collection_id=pk, actor=request.user, notes=notes)
        else:
            raise ValidationError({"action": "Action inconnue."})

        return Response(CollectionSerializer(col, context={"request": request}).data)
