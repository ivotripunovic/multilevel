from django.contrib import admin
from .models import Profile, Commission

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "referral_code", "referred_by", "created_at")
    search_fields = ("user__username","referral_code")

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ("recipient", "amount", "source_user", "level", "created_at")
    list_filter = ("level",)
