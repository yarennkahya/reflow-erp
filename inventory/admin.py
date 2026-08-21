from django.contrib import admin

from .models import Business, Distribution, Lot, Partner, Product, StockMovement


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_type', 'contact_email', 'created_at')
    list_filter = ('business_type',)
    search_fields = ('name', 'contact_email')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit', 'business', 'created_at')
    list_filter = ('category', 'unit', 'business')
    search_fields = ('name',)


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


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity_kg', 'contact_email', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_email')


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = ('lot', 'channel', 'partner', 'quantity', 'decided_at')
    list_filter = ('channel', 'decided_at')
    search_fields = ('lot__lot_code', 'lot__product__name', 'partner__name')
    ordering = ('-decided_at',)
