from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from dashboard.views_helpers import paginate

from .models import AuditLog


@login_required
def audit_list_view(request):
    audit_logs = AuditLog.objects.select_related('user', 'content_type').all()
    # Denetim kaydı sınırsız büyür; sayfalama şart.
    page_obj = paginate(request, audit_logs)
    return render(request, 'audit/list.html', {
        'page_obj': page_obj,
        'audit_logs': page_obj,
        'total_logs': audit_logs.count(),
    })
