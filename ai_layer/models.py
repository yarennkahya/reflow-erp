from django.db import models
from django.utils.translation import gettext_lazy as _
from pgvector.django import VectorField
from django.conf import settings

class Document(models.Model):
    class Source(models.TextChoices):
        PROCEDURE = 'procedure', _('Prosedür / talimat')
        SUPPLIER_NOTE = 'supplier_note', _('Tedarikçi notu')
        GENERAL = 'general', _('Genel bilgi')

    title = models.CharField(max_length=255)
    content = models.TextField()
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.GENERAL
    )
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Conversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations'
    )
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f'Sohbet #{self.pk}'


class ChatMessage(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    role = models.CharField(max_length=20)
    raw_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.conversation} - {self.role}'


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='chunks'
    )
    content = models.TextField()
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['document', 'order']
        unique_together = ('document', 'order')

    def __str__(self):
        return f'{self.document.title} - parça {self.order}'
