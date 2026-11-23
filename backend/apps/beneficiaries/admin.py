from django.contrib import admin

from .models import Beneficiary


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ("full_name", "association", "phone", "city", "household_size", "priority", "is_active")
    list_filter = ("priority", "is_active", "city")
    search_fields = ("first_name", "last_name", "phone", "needs", "association__name")
