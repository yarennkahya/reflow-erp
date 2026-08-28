from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Department, Employee, JobOpening, LeaveRequest

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

_APP_STAGE = {
    'applied':    'bg-secondary-subtle text-secondary',
    'screening':  'bg-info-subtle text-info',
    'interview':  'bg-primary-subtle text-primary',
    'offer':      'bg-warning-subtle text-warning',
    'hired':      'bg-success-subtle text-success',
    'rejected':   'bg-danger-subtle text-danger',
}


def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


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


@login_required
def employee_list_view(request):
    qs = Employee.objects.select_related('department', 'position', 'manager').order_by('name')
    departments = Department.objects.order_by('name')
    dept_id = request.GET.get('department')
    if dept_id:
        qs = qs.filter(department_id=dept_id)
    emp_data = [
        {
            'emp': emp,
            'badge_cls': _EMP_STATUS.get(emp.employment_status, 'bg-secondary-subtle text-secondary'),
        }
        for emp in qs
    ]
    context = {
        'employees': emp_data,
        'departments': departments,
        'selected_dept': dept_id,
    }
    template_name = (
        'hr/partials/employee_results.html'
        if _is_ajax(request) else 'hr/employee_list.html'
    )
    return render(request, template_name, context)


@login_required
def employee_detail_view(request, pk):
    emp = get_object_or_404(
        Employee.objects.select_related('department', 'position', 'manager'),
        pk=pk,
    )
    leave_data = [
        {
            'leave': lr,
            'badge_cls': _LEAVE_STATUS.get(lr.status, 'bg-secondary-subtle text-secondary'),
        }
        for lr in emp.leave_requests.select_related('leave_type').order_by('-requested_at')
    ]
    reports = emp.direct_reports.select_related('department', 'position').order_by('name')
    return render(request, 'hr/employee_detail.html', {
        'emp': emp,
        'badge_cls': _EMP_STATUS.get(emp.employment_status, 'bg-secondary-subtle text-secondary'),
        'leaves': leave_data,
        'reports': reports,
    })


@login_required
def leave_list_view(request):
    qs = LeaveRequest.objects.select_related('employee', 'leave_type', 'approved_by').order_by('-requested_at')
    status_filter = request.GET.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)
    leave_data = [
        {
            'leave': lr,
            'badge_cls': _LEAVE_STATUS.get(lr.status, 'bg-secondary-subtle text-secondary'),
        }
        for lr in qs
    ]
    context = {
        'leaves': leave_data,
        'selected_status': status_filter,
        'status_choices': LeaveRequest.Status.choices,
    }
    template_name = (
        'hr/partials/leave_results.html'
        if _is_ajax(request) else 'hr/leave_list.html'
    )
    return render(request, template_name, context)


@login_required
def recruitment_view(request):
    openings = JobOpening.objects.select_related('department', 'position').prefetch_related(
        'applications__candidate'
    ).order_by('-opened_at')
    openings_data = []
    for opening in openings:
        apps = [
            {
                'app': app,
                'badge_cls': _APP_STAGE.get(app.stage, 'bg-secondary-subtle text-secondary'),
            }
            for app in opening.applications.all()
        ]
        openings_data.append({'opening': opening, 'applications': apps})
    return render(request, 'hr/recruitment.html', {'openings': openings_data})
