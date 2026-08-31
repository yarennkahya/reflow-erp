from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from inventory.models import Lot, Product

from .forms import QualityCheckForm, RecipeForm
from .models import Recipe, RecipeComponent, RoastBatch
from .services import create_roast_batch, perform_quality_check


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
                    user=request.user,
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


@login_required
def recipe_create_view(request):
    form = RecipeForm(request.POST or None)
    products = Product.objects.order_by('name')
    if request.method == 'POST' and form.is_valid():
        product_ids = request.POST.getlist('component_product')
        ratios = request.POST.getlist('component_ratio')
        pairs = [(pid, r) for pid, r in zip(product_ids, ratios) if pid and r]
        if not pairs:
            messages.error(request, 'En az bir bileşen ekleyin.')
        else:
            try:
                with transaction.atomic():
                    recipe = form.save()
                    total = Decimal('0')
                    for pid, ratio in pairs:
                        ratio_d = Decimal(str(ratio))
                        total += ratio_d
                        RecipeComponent.objects.create(
                            recipe=recipe,
                            input_product_id=int(pid),
                            ratio_percent=ratio_d,
                        )
                    if total != Decimal('100'):
                        raise ValueError(f'Bileşen oranları toplamı 100 olmalı, şu an {total}.')
                messages.success(request, f'Reçete "{recipe.name}" oluşturuldu.')
                return redirect('production-recipes')
            except Exception as exc:
                messages.error(request, str(exc))
    return render(request, 'production/recipe_create.html', {'form': form, 'products': products})


@login_required
def batch_create_view(request):
    recipes = Recipe.objects.order_by('name')
    selected_recipe = None
    component_data = []

    recipe_id = request.POST.get('recipe') or request.GET.get('recipe')
    if recipe_id:
        selected_recipe = get_object_or_404(
            Recipe.objects.prefetch_related('components__input_product'),
            pk=recipe_id,
        )
        for component in selected_recipe.components.all():
            available_lots = [
                lot for lot in Lot.objects.filter(
                    product=component.input_product
                ).order_by('expiry_date')
                if lot.remaining_quantity > 0
            ]
            component_data.append({
                'component': component,
                'lots': available_lots,
            })

    if request.method == 'POST' and selected_recipe and 'output_lot_code' in request.POST:
        try:
            output_quantity = Decimal(request.POST['output_quantity'])
            output_lot_code = request.POST['output_lot_code'].strip()
            expiry_str = request.POST['output_expiry_date']
            output_expiry_date = parse_date(expiry_str)
            if not output_lot_code:
                raise ValueError('Çıktı lot kodu zorunludur.')
            if output_expiry_date is None:
                raise ValueError('Geçerli bir çıktı son kullanma tarihi girin.')
            input_lots = {}
            for cd in component_data:
                comp = cd['component']
                lot_id = request.POST.get(f'lot_{comp.input_product_id}')
                if not lot_id:
                    raise ValueError(f'{comp.input_product.name} için lot seçin.')
                try:
                    input_lots[comp.input_product_id] = Lot.objects.get(
                        pk=lot_id,
                        product=comp.input_product,
                    )
                except Lot.DoesNotExist:
                    raise ValueError(
                        f'{comp.input_product.name} için geçerli bir lot seçin.'
                    )
            batch = create_roast_batch(
                recipe=selected_recipe,
                input_lots=input_lots,
                output_quantity=output_quantity,
                output_lot_code=output_lot_code,
                output_expiry_date=output_expiry_date,
            )
            messages.success(request, f'Üretim emri #{batch.pk} oluşturuldu.')
            return redirect('production-batch-detail', pk=batch.pk)
        except Exception as exc:
            messages.error(request, str(exc))

    return render(request, 'production/batch_create.html', {
        'recipes': recipes,
        'selected_recipe': selected_recipe,
        'component_data': component_data,
    })
