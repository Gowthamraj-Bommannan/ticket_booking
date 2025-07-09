from django.contrib import admin
from .models import PaymentTransaction

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'payment_gateway_id', 'amount', 'status', 'payment_method', 'paid_at', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['payment_gateway_id', 'booking__pnr_number']
    ordering = ['-created_at']