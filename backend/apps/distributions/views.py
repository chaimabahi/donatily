from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.pagination import DefaultPagination
from apps.accounts.services import log_activity
from apps.beneficiaries.models import Beneficiary

from .models import Distribution
from .serializers import DistributionSerializer


class DistributionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = Distribution.objects.select_related(
            "association", "beneficiary", "recorded_by"
        ).order_by("-distributed_on", "-created_at")

        if user.role == "association":
            queryset = queryset.filter(association=user.association_profile)
        elif user.role == "admin":
            assoc_id = request.query_params.get("association")
            if assoc_id:
                queryset = queryset.filter(association_id=assoc_id)
        else:
            raise PermissionDenied("Accès interdit.")

        beneficiary_id = request.query_params.get("beneficiary")
        if beneficiary_id:
            queryset = queryset.filter(beneficiary_id=beneficiary_id)

        date_from = request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(distributed_on__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(distributed_on__lte=date_to)

        query = request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(beneficiary__first_name__icontains=query)
                | Q(beneficiary__last_name__icontains=query)
                | Q(notes__icontains=query)
            )

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = DistributionSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role != "association":
            raise PermissionDenied("Seules les associations peuvent enregistrer des distributions.")

        association = request.user.association_profile
        beneficiary_id = request.data.get("beneficiary")
        beneficiary = get_object_or_404(Beneficiary, pk=beneficiary_id)
        if beneficiary.association_id != association.id:
            raise ValidationError({"beneficiary": "Ce bénéficiaire n'appartient pas à votre association."})

        serializer = DistributionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        distribution = serializer.save(association=association, recorded_by=request.user)

        log_activity(
            request.user,
            "distribution.create",
            "distribution",
            distribution.pk,
            f"Distribution « {distribution.title} » enregistrée pour {beneficiary.full_name}.",
        )
        return Response(DistributionSerializer(distribution, context={"request": request}).data, status=status.HTTP_201_CREATED)


class DistributionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        distribution = get_object_or_404(
            Distribution.objects.select_related("association", "beneficiary", "recorded_by"),
            pk=pk,
        )
        is_assoc = user.role == "association" and hasattr(user, "association_profile") and distribution.association_id == user.association_profile.id
        if user.role != "admin" and not is_assoc:
            raise PermissionDenied("Accès interdit.")
        return distribution

    def get(self, request, pk):
        distribution = self.get_object(pk, request.user)
        return Response(DistributionSerializer(distribution, context={"request": request}).data)

    def patch(self, request, pk):
        distribution = self.get_object(pk, request.user)
        serializer = DistributionSerializer(distribution, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        log_activity(
            request.user,
            "distribution.update",
            "distribution",
            updated.pk,
            f"Distribution #{updated.pk} mise à jour.",
        )
        return Response(DistributionSerializer(updated, context={"request": request}).data)

    def delete(self, request, pk):
        distribution = self.get_object(pk, request.user)
        pk_val = distribution.pk
        distribution.delete()
        log_activity(request.user, "distribution.delete", "distribution", pk_val, f"Distribution #{pk_val} supprimée.")
        return Response(status=status.HTTP_204_NO_CONTENT)
