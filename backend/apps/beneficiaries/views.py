from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.pagination import DefaultPagination
from apps.accounts.permissions import IsAssociation
from apps.accounts.services import log_activity

from .models import Beneficiary
from .serializers import BeneficiarySerializer


class BeneficiaryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = Beneficiary.objects.select_related("association").order_by("last_name", "first_name")

        if user.role == "association":
            queryset = queryset.filter(association=user.association_profile)
        elif user.role == "admin":
            assoc_id = request.query_params.get("association")
            if assoc_id:
                queryset = queryset.filter(association_id=assoc_id)
        else:
            raise PermissionDenied("Accès réservé aux associations et administrateurs.")

        priority = request.query_params.get("priority")
        if priority:
            queryset = queryset.filter(priority=priority)

        active = request.query_params.get("active")
        if active in ["true", "false"]:
            queryset = queryset.filter(is_active=(active == "true"))

        city = request.query_params.get("city")
        if city:
            queryset = queryset.filter(city__iexact=city)

        query = request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(phone__icontains=query)
                | Q(needs__icontains=query)
                | Q(city__icontains=query)
            )

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = BeneficiarySerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role != "association":
            raise PermissionDenied("Seules les associations peuvent enregistrer des bénéficiaires.")

        serializer = BeneficiarySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        beneficiary = serializer.save(association=request.user.association_profile)

        log_activity(
            request.user,
            "beneficiary.create",
            "beneficiary",
            beneficiary.pk,
            f"Bénéficiaire {beneficiary.full_name} ajouté.",
        )
        return Response(BeneficiarySerializer(beneficiary, context={"request": request}).data, status=status.HTTP_201_CREATED)


class BeneficiaryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        beneficiary = get_object_or_404(Beneficiary.objects.select_related("association"), pk=pk)
        is_assoc = user.role == "association" and hasattr(user, "association_profile") and beneficiary.association_id == user.association_profile.id
        if user.role != "admin" and not is_assoc:
            raise PermissionDenied("Accès interdit.")
        return beneficiary

    def get(self, request, pk):
        beneficiary = self.get_object(pk, request.user)
        return Response(BeneficiarySerializer(beneficiary, context={"request": request}).data)

    def patch(self, request, pk):
        beneficiary = self.get_object(pk, request.user)
        serializer = BeneficiarySerializer(beneficiary, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        log_activity(
            request.user,
            "beneficiary.update",
            "beneficiary",
            updated.pk,
            f"Bénéficiaire {updated.full_name} mis à jour.",
        )
        return Response(BeneficiarySerializer(updated, context={"request": request}).data)

    def delete(self, request, pk):
        beneficiary = self.get_object(pk, request.user)
        name = beneficiary.full_name
        beneficiary.delete()
        log_activity(request.user, "beneficiary.delete", "beneficiary", pk, f"Bénéficiaire {name} supprimé.")
        return Response(status=status.HTTP_204_NO_CONTENT)
