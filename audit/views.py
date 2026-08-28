from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import AuditLog


@login_required
def audit_list_view(request):
    audit_logs = AuditLog.objects.select_related('user', 'content_type').all()
    return render(request, 'audit/list.html', {'audit_logs': audit_logs})
