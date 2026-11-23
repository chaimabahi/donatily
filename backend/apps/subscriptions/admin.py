from django.contrib import admin

from .models import CreditTransaction, Subscription, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "merchant", "price", "credits", "duration_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "merchant__business_name")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("association", "plan", "status", "start_date", "end_date", "created_at")
    list_filter = ("status",)
    search_fields = ("association__name", "plan__name")


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ("association", "amount", "balance_after", "tx_type", "created_at")
    list_filter = ("tx_type",)
    search_fields = ("association__name", "description")
