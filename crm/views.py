from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Opportunity

_STAGE = {
    'new':           'bg-secondary-subtle text-secondary',
    'in_discussion': 'bg-info-subtle text-info',
    'proposal_sent': 'bg-primary-subtle text-primary',
    'won':           'bg-success-subtle text-success',
    'lost':          'bg-danger-subtle text-danger',
}


@login_required
def opportunity_list(request):
    opps_data = []
    for opp in Opportunity.objects.select_related('customer').order_by('-updated_at'):
        opps_data.append({
            'opp': opp,
            'badge_cls': _STAGE.get(opp.stage, 'bg-secondary-subtle text-secondary'),
        })
    return render(request, 'crm/list.html', {'opportunities': opps_data})
