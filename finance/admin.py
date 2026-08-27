from django.contrib import admin

from .models import Invoice, Payment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'status', 'total_amount', 'balance_due', 'issued_at', 'due_date')
    list_filter = ('status',)
    readonly_fields = ('issued_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice', 'amount', 'method', 'paid_at')
    list_filter = ('method',)
    readonly_fields = ('paid_at',)
