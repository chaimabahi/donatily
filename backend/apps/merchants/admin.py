from django.contrib import admin

from .models import Merchant


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ["business_name", "city", "status", "tax_id", "user"]
    list_filter = ["status", "city"]
    search_fields = ["business_name", "tax_id", "user__email"]
