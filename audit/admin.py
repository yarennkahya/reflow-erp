from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'content_type', 'object_id', 'created_at')
    list_filter = ('action', 'content_type')
    search_fields = ('user__username', 'action', 'details')
    readonly_fields = ('user', 'action', 'content_type', 'object_id', 'details', 'created_at')
