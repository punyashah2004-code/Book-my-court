from django.contrib import admin
from .models import courts,Booking
from django.contrib.sessions.models import Session




admin.site.register(Session)
# Register models
@admin.register(courts)
class CourtAdmin(admin.ModelAdmin):
    list_display = ("name", "game_type", "location", "price", "is_available")
    list_filter = ("game_type", "is_available")
    search_fields = ("name", "location")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("name", "court", "time_slot", "payment_method", "status", "created_at")
    list_filter = ("status", "payment_method", "court")
    search_fields = ("name", "email")


