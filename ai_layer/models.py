from django.db import models
from pgvector.django import VectorField


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