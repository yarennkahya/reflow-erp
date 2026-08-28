from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from hr.models import Employee
from inventory.models import Lot, Product


class Recipe(models.Model):
    name = models.CharField(max_length=255)
    output_product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name='recipes'
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class RecipeComponent(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='components'
    )
    input_product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name='used_in_recipes'
    )
    ratio_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    class Meta:
        unique_together = ('recipe', 'input_product')

    def __str__(self):
        return f'{self.recipe.name}: {self.input_product.name} %{self.ratio_percent}'


class RoastBatch(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.PROTECT, related_name='roast_batches'
    )
    output_lot = models.OneToOneField(
        Lot, on_delete=models.PROTECT, related_name='produced_by_batch'
    )
    total_output_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    roasted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.recipe.name} batch -> {self.output_lot}'


class QualityCheck(models.Model):
    class Result(models.TextChoices):
        PASS = 'pass', 'Geçti'
        FAIL = 'fail', 'Kaldı'

    batch = models.OneToOneField(
        RoastBatch, on_delete=models.PROTECT, related_name='quality_check'
    )
    result = models.CharField(max_length=10, choices=Result.choices)
    score = models.PositiveIntegerField(
        null=True, blank=True, help_text='Cupping skoru (0-100)'
    )
    inspector = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='quality_checks'
    )
    notes = models.TextField(blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.batch} - {self.get_result_display()}'

# Create your models here.
