from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import get_profitability_report


@login_required
def report_view(request):
    report = get_profitability_report()
    return render(request, 'finance/list.html', {'report': report})
