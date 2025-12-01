from django.contrib import admin
from .models import Payment, Transaction, Company, CompanyRevenue


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "payer", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("payer__username",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "payment", "tx_type", "amount", "created_at")
    list_filter = ("tx_type", "created_at")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner")
    list_filter = ("created_at",)


@admin.register(CompanyRevenue)
class CompanyRevenueAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "total_revenue")
