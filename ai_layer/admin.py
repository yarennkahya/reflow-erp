from django.contrib import admin

from .models import ChatMessage, Conversation, Document, DocumentChunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'created_at')
    list_filter = ('source',)
    search_fields = ('title', 'content')


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ('document', 'order', 'content_preview')
    list_filter = ('document',)

    @admin.display(description='İçerik')
    def content_preview(self, obj):
        return f'{obj.content[:50]}…' if len(obj.content) > 50 else obj.content


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'updated_at')
    list_filter = ('user',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'role', 'created_at')
    list_filter = ('role',)
