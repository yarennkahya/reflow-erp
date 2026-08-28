from django.contrib import admin

from .models import Business, Lot, Product, StockMovement , Warehouse



@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_type', 'contact_email', 'is_active', 'created_at')
    list_filter = ('business_type', 'is_active')
    search_fields = ('name', 'contact_email')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit', 'business', 'reorder_point', 'reorder_quantity', 'created_at')
    list_filter = ('category', 'unit', 'business')
    search_fields = ('name',)
    list_editable = ('reorder_point', 'reorder_quantity')


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ('lot_code', 'product', 'expiry_date', 'quantity_received', 'received_at')
    list_filter = ('expiry_date', 'product')
    search_fields = ('lot_code', 'product__name')
    ordering = ('expiry_date', 'received_at')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('lot', 'movement_type', 'quantity', 'created_at')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('lot__lot_code', 'lot__product__name')
    ordering = ('-created_at',)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'is_active')
    list_filter = ('is_active', 'city')
