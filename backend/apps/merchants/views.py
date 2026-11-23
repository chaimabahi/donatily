from django.db.models import Count, Q
from django.http import Http404
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.pagination import DefaultPagination
from apps.accounts.permissions import IsMerchant

from .models import Merchant
from .serializers import MerchantSerializer


def annotated_merchants():
    return Merchant.objects.select_related("user").annotate(
        published_products=Count("products", filter=Q(products__status="approved")),
        active_plans=Count("plans", filter=Q(plans__is_active=True)),
    )


class MerchantMeView(RetrieveUpdateAPIView):
    permission_classes = [IsMerchant]
    serializer_class = MerchantSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_object(self):
        return annotated_merchants().get(pk=self.request.user.merchant_profile.pk)


class MerchantListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = annotated_merchants().order_by("business_name")
        if request.user.role != "admin":
            queryset = queryset.filter(status=Merchant.Status.APPROVED, user__is_active=True)
        status_filter = request.query_params.get("status")
        if status_filter and request.user.role == "admin":
            queryset = queryset.filter(status=status_filter)
        city = request.query_params.get("city")
        query = request.query_params.get("q")
        if city:
            queryset = queryset.filter(city__iexact=city)
        if query:
            queryset = queryset.filter(
                Q(business_name__icontains=query) | Q(description__icontains=query) | Q(city__icontains=query)
            )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(MerchantSerializer(page, many=True, context={"request": request}).data)


class MerchantDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            merchant = annotated_merchants().get(pk=pk)
        except Merchant.DoesNotExist as exc:
            raise Http404("Commerçant introuvable.") from exc
        is_owner = request.user.role == "merchant" and merchant.user_id == request.user.id
        if request.user.role != "admin" and not is_owner and merchant.status != Merchant.Status.APPROVED:
            raise Http404("Commerçant introuvable.")
        return Response(MerchantSerializer(merchant, context={"request": request}).data)
