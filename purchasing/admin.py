from django.contrib import admin

from .models import GoodsReceipt, PurchaseOrder, PurchaseOrderItem


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'status', 'expected_delivery_date', 'created_at', 'updated_at')
    list_filter = ('status', 'supplier')
    inlines = [PurchaseOrderItemInline]
    ordering = ('-created_at',)


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ('purchase_order_item', 'lot', 'quantity_received', 'received_at')
    list_filter = ('received_at',)
    ordering = ('-received_at',)
