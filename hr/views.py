import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dashboard.calendars import month_grid_spans, normalize_period, period_nav
from dashboard.grouping import group_by_choice
from dashboard.views_helpers import is_ajax, paginate, pick_view

from .forms import ApplicationForm, CandidateDocumentForm, CandidateForm, EmployeeForm, JobOpeningForm, LeaveRequestForm
from .models import Application, Candidate, CandidateDocument, Department, Employee, JobOpening, LeaveRequest, Position
from .services import (
    advance_application_stage,
    set_application_stage,
    set_employment_status,
    approve_leave_request,
    check_meeting_conflicts,
    reject_application,
    reject_leave_request,
)


@login_required
def hr_list(request):
    # Rozet sınıfları artık {% ui_badge %} tarafından üretiliyor; view'ın
    # sarmalayıcı sözlük kurmasına gerek kalmadı.
    return render(request, 'hr/list.html', {
        'employees': Employee.objects.select_related(
            'department', 'position', 'manager').order_by('name'),
        'leaves': LeaveRequest.objects.filter(
            status=LeaveRequest.Status.PENDING
        ).select_related('employee', 'leave_type'),
        'employee_count': Employee.objects.count(),
        'active_count': Employee.objects.filter(
            employment_status=Employee.EmploymentStatus.ACTIVE).count(),
        'pending_leaves': LeaveRequest.objects.filter(
            status=LeaveRequest.Status.PENDING).count(),
        'open_positions': JobOpening.objects.filter(
            status=JobOpening.Status.OPEN).count(),
    })


@login_required
def employee_list_view(request):
    qs = Employee.objects.select_related('department', 'position', 'manager').order_by('name')
    departments = Department.objects.order_by('name')
    dept_id = request.GET.get('department')
    manager_id = request.GET.get('manager')
    selected_status = request.GET.get('status', '')

    if manager_id:
        manager = Employee.objects.filter(pk=manager_id).first()
        qs = (
            manager.direct_reports.select_related('department', 'position', 'manager').order_by('name')
            if manager else Employee.objects.none()
        )
    if dept_id:
        qs = qs.filter(department_id=dept_id)
    if selected_status in Employee.EmploymentStatus.values:
        qs = qs.filter(employment_status=selected_status)
    else:
        selected_status = ''

    view = pick_view(request, ('list', 'kanban', 'card'))
    employees = list(qs)
    page_obj = paginate(request, employees) if view == 'list' else None

    context = {
        'view': view,
        'view_template': f'hr/_employees_{view}.html',
        'page_obj': page_obj,
        'employees': list(page_obj) if page_obj is not None else employees,
        'columns': (
            group_by_choice(
                employees, 'employment_status', Employee.EmploymentStatus.choices,
            ) if view == 'kanban' else None
        ),
        'employee_count': len(employees),
        'departments': departments,
        'managers': Employee.objects.filter(direct_reports__isnull=False).distinct().order_by('name'),
        'selected_dept': dept_id,
        'selected_manager': manager_id,
        'status_choices': Employee.EmploymentStatus.choices,
        'selected_status': selected_status,
    }
    return render(request, 'hr/employee_list.html', context)


@login_required
def employee_detail_view(request, pk):
    emp = get_object_or_404(
        Employee.objects.select_related('department', 'position', 'manager'),
        pk=pk,
    )
    leaves = emp.leave_requests.select_related('leave_type').order_by('-requested_at')
    reports = emp.direct_reports.select_related('department', 'position').order_by('name')
    return render(request, 'hr/employee_detail.html', {
        'emp': emp,
        'leaves': leaves,
        'reports': reports,
    })


def _positions_json():
    """Departman → pozisyon listesi; form şablonlarındaki cascade için."""
    data = {}
    for pos in Position.objects.select_related('department').order_by('title'):
        key = str(pos.department_id)
        data.setdefault(key, []).append({'id': pos.pk, 'title': pos.title})
    return json.dumps(data)


@login_required
def employee_create_view(request):
    form = EmployeeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        emp = form.save()
        messages.success(request, f'{emp.name} çalışan olarak eklendi.')
        return redirect('hr-employee-detail', pk=emp.pk)
    return render(request, 'hr/employee_form.html', {
        'form': form, 'positions_json': _positions_json(),
    })


@login_required
def employee_edit_view(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, instance=emp)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{emp.name} güncellendi.')
        return redirect('hr-employee-detail', pk=emp.pk)
    return render(request, 'hr/employee_form.html', {
        'form': form, 'employee': emp, 'positions_json': _positions_json(),
    })


@login_required
def leave_list_view(request):
    qs = LeaveRequest.objects.select_related('employee', 'leave_type', 'approved_by').order_by('-requested_at')
    status_filter = request.GET.get('status')
    if status_filter == 'all':
        status_filter = None
    if status_filter:
        qs = qs.filter(status=status_filter)
    leaves = list(qs)
    view = pick_view(request, ('list', 'calendar'))
    page_obj = paginate(request, leaves) if view == 'list' else None

    calendar_ctx = {}
    if view == 'calendar':
        year, month = normalize_period(request.GET.get('year'), request.GET.get('month'))
        calendar_ctx = period_nav(year, month)
        # İzinler tek gün değil ARALIK; bu yüzden span-duyarlı ızgara.
        calendar_ctx['weeks'] = month_grid_spans(
            year, month, leaves,
            start_of=lambda leave: leave.start_date,
            end_of=lambda leave: leave.end_date,
        )

    context = {
        'view': view,
        'view_template': f'hr/_leaves_{view}.html',
        'page_obj': page_obj,
        'leaves': list(page_obj) if page_obj is not None else leaves,
        **calendar_ctx,
        'selected_status': status_filter or 'all',
        'status_choices': LeaveRequest.Status.choices,
        'employees': Employee.objects.all(),
        'pending_count': LeaveRequest.objects.filter(
            status=LeaveRequest.Status.PENDING).count(),
    }
    return render(request, 'hr/leave_list.html', context)


@login_required
def leave_request_create_view(request):
    form = LeaveRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        leave_request = form.save()
        messages.success(
            request,
            f'{leave_request.employee.name} için izin talebi oluşturuldu.',
        )
        return redirect('hr-leave')
    return render(request, 'hr/leave_request_form.html', {'form': form})


@login_required
def leave_approve_view(request, pk):
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == 'POST':
        approver_id = request.POST.get('approver')
        approver = get_object_or_404(Employee, pk=approver_id) if approver_id else None
        conflicts = check_meeting_conflicts(leave_request)
        try:
            approve_leave_request(leave_request, approved_by=approver)
            if conflicts.exists():
                names = ', '.join(m.title for m in conflicts)
                messages.warning(
                    request,
                    f'{leave_request.employee.name} bu tarihlerde şu '
                    f'toplantılarla çakışıyor: {names}. İzin yine de '
                    f'onaylandı.'
                )
            else:
                messages.success(request, 'İzin talebi onaylandı.')
        except ValueError as exc:
            messages.error(request, str(exc))
    return redirect('hr-leave')


@login_required
def leave_reject_view(request, pk):
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == 'POST':
        approver_id = request.POST.get('approver')
        approver = get_object_or_404(Employee, pk=approver_id) if approver_id else None
        try:
            reject_leave_request(leave_request, approved_by=approver)
            messages.success(request, 'İzin talebi reddedildi.')
        except ValueError as exc:
            messages.error(request, str(exc))
    return redirect('hr-leave')


@login_required
def recruitment_view(request):
    selected_dept = request.GET.get('department', '')
    openings_qs = (
        JobOpening.objects.select_related('department', 'position')
        .annotate(
            hired_count=Count(
                'applications',
                filter=Q(applications__stage=Application.Stage.HIRED),
            )
        )
        .prefetch_related('applications__candidate')
        .order_by('-opened_at')
    )
    if selected_dept:
        openings_qs = openings_qs.filter(department_id=selected_dept)
    openings = openings_qs
    openings_data = [
        {
            'opening': opening,
            'applications': list(opening.applications.all()),
            'occupancy_percent': round(opening.hired_count * 100 / opening.headcount)
            if opening.headcount else 0,
        }
        for opening in openings
    ]

    # Açık pozisyonlardaki başvurular — kanban kolonlarının kaynağı.
    active_applications = list(
        Application.objects.filter(job_opening__status=JobOpening.Status.OPEN)
        .select_related('candidate', 'job_opening')
        .order_by('-updated_at')
    )

    view = pick_view(request, ('kanban', 'list'), default='kanban')

    dept_choices = [(str(d.pk), d.name) for d in Department.objects.order_by('name')]
    return render(request, 'hr/recruitment.html', {
        'view': view,
        'view_template': f'hr/_recruitment_{view}.html',
        'openings': openings_data,
        'applications': active_applications,
        'columns': (
            group_by_choice(active_applications, 'stage', Application.Stage.choices)
            if view == 'kanban' else None
        ),
        'open_count': JobOpening.objects.filter(status=JobOpening.Status.OPEN).count(),
        'candidate_count': Candidate.objects.count(),
        'application_count': len(active_applications),
        'dept_choices': dept_choices,
        'selected_dept': selected_dept,
    })


@login_required
def job_opening_create_view(request):
    form = JobOpeningForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        opening = form.save()
        messages.success(request, f'{opening.title} pozisyonu açık olarak oluşturuldu.')
        return redirect('hr-recruitment')
    return render(request, 'hr/job_opening_form.html', {
        'form': form, 'positions_json': _positions_json(),
    })


@login_required
def candidates_pool_view(request):
    stage_filter = request.GET.get('stage', 'active')

    terminal_hired = Application.Stage.HIRED
    terminal_rejected = Application.Stage.REJECTED
    active_stages = [
        Application.Stage.APPLIED, Application.Stage.SCREENING,
        Application.Stage.INTERVIEW, Application.Stage.OFFER,
    ]

    if stage_filter == 'hired':
        apps = Application.objects.filter(stage=terminal_hired)
    elif stage_filter == 'rejected':
        apps = Application.objects.filter(stage=terminal_rejected)
    else:
        stage_filter = 'active'
        apps = Application.objects.filter(stage__in=active_stages)

    apps = apps.select_related('candidate', 'job_opening').order_by('-updated_at')

    return render(request, 'hr/candidates.html', {
        'applications': apps,
        'stage_filter': stage_filter,
        'active_count': Application.objects.filter(stage__in=active_stages).count(),
        'hired_count': Application.objects.filter(stage=terminal_hired).count(),
        'rejected_count': Application.objects.filter(stage=terminal_rejected).count(),
    })


@login_required
def candidate_detail_view(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    documents = candidate.documents.all()
    applications = candidate.applications.select_related('job_opening').order_by('-applied_at')
    doc_form = CandidateDocumentForm()
    return render(request, 'hr/candidate_detail.html', {
        'candidate': candidate,
        'documents': documents,
        'applications': applications,
        'doc_form': doc_form,
    })


@login_required
@require_POST
def candidate_document_upload_view(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    form = CandidateDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.candidate = candidate
        doc.save()
        messages.success(request, 'Dosya yüklendi.')
    else:
        messages.error(request, 'Dosya yüklenemedi.')
    return redirect('hr-candidate-detail', pk=pk)


@login_required
def candidate_create_view(request):
    form = CandidateForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        candidate = form.save()
        cv_file = form.cleaned_data.get('cv_file')
        if cv_file:
            CandidateDocument.objects.create(candidate=candidate, file=cv_file, label='CV')
        messages.success(request, f'{candidate.name} adayı oluşturuldu.')
        return redirect('hr-candidate-detail', pk=candidate.pk)
    return render(request, 'hr/candidate_form.html', {'form': form})


@login_required
def application_create_view(request):
    form = ApplicationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        application = form.save()
        messages.success(request, f'{application.candidate.name} için başvuru oluşturuldu.')
        return redirect('hr-recruitment')
    return render(request, 'hr/application_form.html', {'form': form})


@login_required
@require_POST
def application_advance_view(request, pk):
    application = get_object_or_404(Application, pk=pk)
    try:
        advance_application_stage(application)
        messages.success(
            request,
            f'{application.candidate.name} → {application.get_stage_display()}',
        )
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('hr-recruitment')


@login_required
@require_POST
def application_reject_view(request, pk):
    application = get_object_or_404(Application, pk=pk)
    try:
        reject_application(application)
        messages.success(request, f'{application.candidate.name} başvurusu reddedildi.')
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('hr-recruitment')


@login_required
@require_POST
def application_set_stage_view(request, pk):
    """Kanban sürükle-bırak hedefi. JSON döner; JS kartı geri alabilsin diye
    hata durumunda 400 + mesaj verir."""
    obj = get_object_or_404(Application, pk=pk)
    try:
        set_application_stage(obj, request.POST.get('stage', ''))
    except ValueError as error:
        return JsonResponse({'ok': False, 'error': str(error)}, status=400)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def employee_set_status_view(request, pk):
    """Kanban sürükle-bırak hedefi. JSON döner; JS kartı geri alabilsin diye
    hata durumunda 400 + mesaj verir."""
    obj = get_object_or_404(Employee, pk=pk)
    try:
        set_employment_status(obj, request.POST.get('stage', ''))
    except ValueError as error:
        return JsonResponse({'ok': False, 'error': str(error)}, status=400)
    return JsonResponse({'ok': True})
