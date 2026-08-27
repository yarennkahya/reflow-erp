from django.contrib import admin

from .models import Opportunity


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'customer', 'status', 'stage', 'estimated_value', 'updated_at')
    list_filter = ('status', 'stage')
    search_fields = ('title', 'customer__name')
    ordering = ('-updated_at',)
