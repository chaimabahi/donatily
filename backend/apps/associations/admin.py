from django.contrib import admin

from .models import Association


@admin.register(Association)
class AssociationAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "status", "credit_balance", "user"]
    list_filter = ["status", "city"]
    search_fields = ["name", "registration_number", "user__email"]
