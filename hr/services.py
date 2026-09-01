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




# Basvuru hattinin sirasi. REDDEDILDI bu siranin disindadir (kapanmis kayit),
# tipki crm.services.STAGE_ORDER'da LOST'un disarida kalmasi gibi.
APPLICATION_STAGE_ORDER = [
    Application.Stage.APPLIED,
    Application.Stage.SCREENING,
    Application.Stage.INTERVIEW,
    Application.Stage.OFFER,
    Application.Stage.HIRED,
]


def advance_application_stage(application, hire_date=None):
    """
    Basvuruyu bir sonraki asamaya tasir.

    Son adim (ISE ALINDI) hire_candidate()'ten gecer: Employee kaydi olusur ve
    pozisyonun kontenjani dolarsa JobOpening FILLED yapilir. Yani kanban'daki
    ok butonu, dogrudan alan yazmak yerine mevcut is kuralini calistirir.
    """
    if application.stage == Application.Stage.REJECTED:
        raise ValueError('Reddedilmiş bir başvuru ilerletilemez.')
    if application.stage not in APPLICATION_STAGE_ORDER:
        raise ValueError('Bu başvuru ilerletilemez.')

    index = APPLICATION_STAGE_ORDER.index(application.stage)
    if index == len(APPLICATION_STAGE_ORDER) - 1:
        raise ValueError('Bu başvuru zaten işe alındı.')

    next_stage = APPLICATION_STAGE_ORDER[index + 1]

    if next_stage == Application.Stage.HIRED:
        from django.utils import timezone
        hire_candidate(application, hire_date or timezone.localdate())
        return application

    application.stage = next_stage
    application.save(update_fields=['stage', 'updated_at'])
    return application


def reject_application(application):
    """Basvuruyu reddedildi olarak kapatir."""
    if application.stage == Application.Stage.HIRED:
        raise ValueError('İşe alınmış bir başvuru reddedilemez.')
    application.stage = Application.Stage.REJECTED
    application.save(update_fields=['stage', 'updated_at'])
    return application


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


def set_application_stage(application, stage, hire_date=None):
    """Kanban surukle-birak: basvuruyu dogrudan hedef asamaya tasir."""
    if stage not in Application.Stage.values:
        raise ValueError('Geçersiz aşama.')
    if stage == application.stage:
        return application

    if stage == Application.Stage.REJECTED:
        return reject_application(application)

    if application.stage == Application.Stage.HIRED:
        raise ValueError('İşe alınmış bir başvurunun aşaması değiştirilemez.')

    if stage == Application.Stage.HIRED:
        from django.utils import timezone
        hire_candidate(application, hire_date or timezone.localdate())
        application.refresh_from_db()
        return application

    application.stage = stage
    application.save(update_fields=['stage', 'updated_at'])
    return application


def set_employment_status(employee, status):
    """Calisan kanban'i icin istihdam durumunu degistirir."""
    if status not in Employee.EmploymentStatus.values:
        raise ValueError('Geçersiz istihdam durumu.')
    employee.employment_status = status
    employee.save(update_fields=['employment_status'])
    return employee
