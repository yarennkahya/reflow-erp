from django.db import transaction

from .models import Application, Employee, JobOpening, LeaveRequest


def _resolve_leave_request(leave_request, new_status, approved_by):
    if leave_request.status != LeaveRequest.Status.PENDING:
        raise ValueError(
            f'Leave request is not pending (current status: {leave_request.status}).'
        )
    with transaction.atomic():
        leave_request.status = new_status
        leave_request.approved_by = approved_by
        leave_request.save(update_fields=['status', 'approved_by'])
    return leave_request


def approve_leave_request(leave_request, approved_by):
    """Bekleyen bir izin talebini onaylar."""
    return _resolve_leave_request(leave_request, LeaveRequest.Status.APPROVED, approved_by)


def reject_leave_request(leave_request, approved_by):
    """Bekleyen bir izin talebini reddeder."""
    return _resolve_leave_request(leave_request, LeaveRequest.Status.REJECTED, approved_by)




def hire_candidate(application, hire_date, salary=None, manager=None):
    """
    Bir basvuruyu ise alir: Employee kaydi otomatik olusturulur (JobOpening'in
    department/position bilgisinden), Application HIRED olarak isaretlenir,
    JobOpening FILLED yapilir. RoastBatch/GoodsReceipt ile ayni desen: bir
    olay, otomatik olarak baska bir kaydi doguruyor.
    """
    if application.stage == Application.Stage.HIRED:
        raise ValueError('This application is already hired.')

    job_opening = application.job_opening
    candidate = application.candidate

    with transaction.atomic():
        employee = Employee.objects.create(
            name=candidate.name,
            department=job_opening.department,
            position=job_opening.position,
            manager=manager,
            hire_date=hire_date,
            salary=salary,
            email=candidate.email,
            phone=candidate.phone,
        )

        application.stage = Application.Stage.HIRED
        application.save(update_fields=['stage'])

        job_opening.status = JobOpening.Status.FILLED
        job_opening.save(update_fields=['status'])

    return employee