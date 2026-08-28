from django.contrib import admin

from .models import Customer, Order, OrderItem, ReturnRequest


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer_type', 'contact_email', 'created_at')
    list_filter = ('customer_type',)
    search_fields = ('name', 'contact_email')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'status', 'created_at', 'fulfilled_at')
    list_filter = ('status', 'customer__customer_type')
    inlines = [OrderItemInline]
    ordering = ('-created_at',)


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = (
        'order_item',
        'reason',
        'quantity',
        'status',
        'requested_at',
        'resolved_at',
    )
    list_filter = ('status', 'reason')
