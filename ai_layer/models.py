from django.db import models
from pgvector.django import VectorField
from django.conf import settings

class Document(models.Model):
    class Source(models.TextChoices):
        PROCEDURE = 'procedure', 'Prosedür / talimat'
        SUPPLIER_NOTE = 'supplier_note', 'Tedarikçi notu'
        GENERAL = 'general', 'Genel bilgi'

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