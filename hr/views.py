from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Employee, LeaveRequest

_EMP_STATUS = {
    'active':     'bg-success-subtle text-success',
    'on_leave':   'bg-warning-subtle text-warning',
    'terminated': 'bg-secondary-subtle text-secondary',
}

_LEAVE_STATUS = {
    'pending':  'bg-warning-subtle text-warning',
    'approved': 'bg-success-subtle text-success',
    'rejected': 'bg-danger-subtle text-danger',
}


@login_required
def hr_list(request):
    emp_data = [
        {
            'emp': emp,
            'badge_cls': _EMP_STATUS.get(emp.employment_status, 'bg-secondary-subtle text-secondary'),
        }
        for emp in Employee.objects.select_related('department', 'position', 'manager').order_by('name')
    ]
    leave_data = [
        {
            'leave': lr,
            'badge_cls': _LEAVE_STATUS.get(lr.status, 'bg-secondary-subtle text-secondary'),
        }
        for lr in LeaveRequest.objects.filter(status='pending').select_related('employee', 'leave_type')
    ]
    return render(request, 'hr/list.html', {'employees': emp_data, 'leaves': leave_data})
