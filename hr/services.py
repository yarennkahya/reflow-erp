from django.db import transaction
from django.db.models import Q

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
        job_opening = JobOpening.objects.select_for_update().get(pk=job_opening.pk)
        hired_count = Application.objects.filter(
            job_opening=job_opening,
            stage=Application.Stage.HIRED,
        ).count()
        if hired_count >= job_opening.headcount:
            raise ValueError('Bu pozisyonun kontenjanı zaten dolu.')

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

        if hired_count + 1 == job_opening.headcount:
            job_opening.status = JobOpening.Status.FILLED
            job_opening.save(update_fields=['status'])

    return employee


def check_meeting_conflicts(leave_request):
    """
    Bir izin talebinin tarih aralığıyla, çalışanın organizatör veya
    katılımcı olduğu, iptal edilmemiş toplantılar arasında çakışma
    olup olmadığını kontrol eder. Engellemez, sadece bilgi amaçlıdır.
    """
    from meetings.models import Meeting
    employee = leave_request.employee
    return (
        Meeting.objects.filter(status='scheduled')
        .filter(Q(organizer=employee) | Q(attendees=employee))
        .filter(
            start_time__date__lte=leave_request.end_date,
            end_time__date__gte=leave_request.start_date,
        )
        .distinct()
    )
