from django.contrib import admin
from .models import Company, CompanyRevenue, Payment, Transaction


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__username")


@admin.register(CompanyRevenue)
class CompanyRevenueAdmin(admin.ModelAdmin):
    list_display = ("company", "total_revenue", "last_updated")
    readonly_fields = ("last_updated",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "payer", "amount", "fee", "currency", "status", "created_at")
    list_filter = ("status", "currency", "company")
    search_fields = ("external_id", "payer__username", "company__name")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "tx_type", "amount", "fee", "created_at")
    list_filter = ("tx_type", "company")