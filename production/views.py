from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import RoastBatch


@login_required
def batch_list(request):
    batches = RoastBatch.objects.select_related(
        'recipe', 'output_lot__product', 'output_lot__warehouse'
    ).order_by('-roasted_at')
    return render(request, 'production/list.html', {'batches': batches})
