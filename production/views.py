from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.utils.dateparse import parse_date

from dashboard.grouping import group_by_choice
from dashboard.views_helpers import paginate, pick_view
from inventory.models import Lot, Product

from .forms import QualityCheckForm, RecipeForm
from .models import QualityCheck, Recipe, RecipeComponent, RoastBatch
from .services import create_roast_batch, perform_quality_check


@login_required
def batch_list(request):
    batches = list(
        RoastBatch.objects.select_related(
            'recipe', 'output_lot__product', 'output_lot__warehouse', 'quality_check',
        ).order_by('-roasted_at')
    )

    view = pick_view(request, ('list', 'kanban'))
    page_obj = paginate(request, batches) if view == 'list' else None

    # Kalite kontrolü henüz yapılmamış partiler için sentetik bir kolon.
    qc_choices = list(QualityCheck.Result.choices) + [('pending', _('Kalite kontrolü bekliyor'))]

    def qc_key(batch):
        check = getattr(batch, 'quality_check', None)
        return check.result if check else 'pending'

    return render(request, 'production/list.html', {
        'view': view,
        'view_template': f'production/_batches_{view}.html',
        'page_obj': page_obj,
        'batches': list(page_obj) if page_obj is not None else batches,
        'columns': (
            group_by_choice(batches, 'quality', qc_choices, key=qc_key)
            if view == 'kanban' else None
        ),
        'batch_count': len(batches),
        'pending_qc': sum(1 for b in batches if qc_key(b) == 'pending'),
        'recipe_count': Recipe.objects.count(),
    })


@login_required
def recipe_list_view(request):
    recipes = Recipe.objects.prefetch_related(
        'components__input_product'
    ).select_related('output_product').order_by('name')
    page_obj = paginate(request, list(recipes))
    return render(request, 'production/recipe_list.html', {
        'page_obj': page_obj,
        'recipes': page_obj,
        'recipe_count': Recipe.objects.count(),
    })


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
        # AuditLog kaydı partiye değil QualityCheck'e bağlı; chatter'ın
        # bulabilmesi için ilişkili nesneyi ayrıca veriyoruz.
        'quality_check_list': [quality_check] if quality_check else [],
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
