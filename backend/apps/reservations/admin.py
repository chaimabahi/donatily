from django.contrib import admin

from .models import Collection, Reservation, ReservationItem


class ReservationItemInline(admin.TabularInline):
    model = ReservationItem
    extra = 0


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "association", "merchant", "status", "pickup_date", "credits_spent", "created_at")
    list_filter = ("status", "pickup_date")
    search_fields = ("association__name", "merchant__business_name")
    inlines = [ReservationItemInline]


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("id", "reservation", "status", "scheduled_for", "completed_at", "organized_by")
    list_filter = ("status", "scheduled_for")
    search_fields = ("reservation__association__name", "reservation__merchant__business_name")
