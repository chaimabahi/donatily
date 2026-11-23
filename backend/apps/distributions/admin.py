from django.contrib import admin

from .models import Distribution


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = ("title", "association", "beneficiary", "quantity", "unit", "distributed_on", "recorded_by")
    list_filter = ("distributed_on", "unit")
    search_fields = ("title", "association__name", "beneficiary__first_name", "beneficiary__last_name")
