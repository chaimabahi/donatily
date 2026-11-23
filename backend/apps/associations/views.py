from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.pagination import DefaultPagination
from apps.accounts.permissions import IsAdmin, IsAssociation

from .models import Association
from .serializers import AssociationSerializer


class AssociationMeView(RetrieveUpdateAPIView):
    permission_classes = [IsAssociation]
    serializer_class = AssociationSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_object(self):
        return self.request.user.association_profile


class AssociationListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = Association.objects.select_related("user").order_by("name")
        status_filter = request.query_params.get("status")
        query = request.query_params.get("q")
        city = request.query_params.get("city")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if city:
            queryset = queryset.filter(city__iexact=city)
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(city__icontains=query) | Q(registration_number__icontains=query) | Q(user__email__icontains=query)
            )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(AssociationSerializer(page, many=True, context={"request": request}).data)


class AssociationDetailView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        association = get_object_or_404(Association.objects.select_related("user"), pk=pk)
        return Response(AssociationSerializer(association, context={"request": request}).data)
