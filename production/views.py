from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import QualityCheckForm
from .models import Recipe, RoastBatch
from .services import perform_quality_check


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
            'recipe__output_product',
            'output_lot__product',
            'output_lot__warehouse',
            'quality_check__inspector',
        ).prefetch_related('recipe__components__input_product'),
        pk=pk,
    )
    quality_check = batch.quality_check if hasattr(batch, 'quality_check') else None
    quality_check_form = QualityCheckForm(request.POST or None)

    if request.method == 'POST':
        if quality_check:
            messages.error(request, 'Bu parti için zaten bir kalite kontrolü yapılmış.')
            return redirect('production-batch-detail', pk=batch.pk)
        if quality_check_form.is_valid():
            try:
                quality_check = perform_quality_check(
                    batch=batch,
                    result=quality_check_form.cleaned_data['result'],
                    inspector=quality_check_form.cleaned_data['inspector'],
                    score=quality_check_form.cleaned_data['score'],
                    notes=quality_check_form.cleaned_data['notes'],
                )
            except ValueError as error:
                messages.error(request, str(error))
            else:
                messages.success(
                    request,
                    f'Kalite kontrolü “{quality_check.get_result_display()}” olarak kaydedildi.',
                )
                return redirect('production-batch-detail', pk=batch.pk)

    return render(request, 'production/batch_detail.html', {
        'batch': batch,
        'quality_check': quality_check,
        'quality_check_form': quality_check_form,
    })
