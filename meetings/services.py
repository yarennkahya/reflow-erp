from django.utils.dateparse import parse_datetime


def parse_meeting_datetime(value):
    """
    POST'tan gelen datetime-local string'ini gercek datetime nesnesine
    cevirir. Halihazirda zaten bir datetime ise oldugu gibi doner.
    """
    if isinstance(value, str):
        return parse_datetime(value)
    return value


def check_leave_conflicts(start_time, end_time, employee_ids):
    """
    Verilen zaman araligiyla, verilen calisanlarin ONAYLANMIS izin
    talepleri arasinda cakisma olup olmadigini kontrol eder. Engellemez,
    sadece bilgi amaclidir -- hr.services.check_meeting_conflicts'in ters
    yonlu (toplanti -> izin) karsiligi.
    """
    from hr.models import LeaveRequest

    start_time = parse_meeting_datetime(start_time)
    end_time = parse_meeting_datetime(end_time)
    if not start_time or not end_time:
        return LeaveRequest.objects.none()

    return (
        LeaveRequest.objects.filter(
            employee_id__in=employee_ids,
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=end_time.date(),
            end_date__gte=start_time.date(),
        )
        .select_related('employee')
        .distinct()
    )
