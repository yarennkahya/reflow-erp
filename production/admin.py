from django.contrib import admin

from .models import QualityCheck, Recipe, RecipeComponent, RoastBatch


class RecipeComponentInline(admin.TabularInline):
    model = RecipeComponent
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'output_product', 'created_at')
    search_fields = ('name',)
    inlines = [RecipeComponentInline]


@admin.register(RoastBatch)
class RoastBatchAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'output_lot', 'total_output_quantity', 'roasted_at')
    list_filter = ('recipe',)
    ordering = ('-roasted_at',)


@admin.register(QualityCheck)
class QualityCheckAdmin(admin.ModelAdmin):
    list_display = ('batch', 'result', 'score', 'inspector', 'checked_at')

# Register your models here.
