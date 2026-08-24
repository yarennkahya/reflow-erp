from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'created_at')
    list_filter = ('source',)
    search_fields = ('title', 'content')