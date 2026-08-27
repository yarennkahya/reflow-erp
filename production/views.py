from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Recipe, RoastBatch


@login_required
def batch_list(request):
    batches = RoastBatch.objects.select_related(
        'recipe', 'output_lot__product', 'output_lot__warehouse'
    ).order_by('-roasted_at')
    return render(request, 'production/list.html', {'batches': batches})


@login_required
def recipe_list_view(request):
    recipes = Recipe.objects.prefetch_related(
        'components__input_product'
    ).select_related('output_product').order_by('name')
    return render(request, 'production/recipe_list.html', {'recipes': recipes})


@login_required
def batch_detail_view(request, pk):
    batch = get_object_or_404(
        RoastBatch.objects.select_related(
            'recipe__output_product', 'output_lot__product', 'output_lot__warehouse'
        ).prefetch_related('recipe__components__input_product'),
        pk=pk,
    )
    return render(request, 'production/batch_detail.html', {'batch': batch})
