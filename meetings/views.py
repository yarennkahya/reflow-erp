import calendar as pycal
import json
from datetime import date, datetime as dt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from hr.models import Employee

from .models import Meeting
from .services import check_leave_conflicts
from .tasks import send_meeting_invites_task


MONTH_NAMES = [
    '', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
    'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
]


@login_required
def calendar_view(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (TypeError, ValueError):
        year, month = today.year, today.month

    if not 1 <= year <= 9999 or not 1 <= month <= 12:
        year, month = today.year, today.month

    cal = pycal.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)

    meetings = Meeting.objects.filter(
        start_time__year=year, start_time__month=month
    ).select_related('organizer', 'customer')
    meetings_by_day = {}
    for meeting in meetings:
        meetings_by_day.setdefault(meeting.start_time.day, []).append(meeting)

    weeks = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                week_data.append({
                    'day': day,
                    'meetings': meetings_by_day.get(day, []),
                    'is_today': date(year, month, day) == today,
                })
        weeks.append(week_data)

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)

    upcoming = Meeting.objects.filter(
        start_time__gte=timezone.now(), status='scheduled'
    ).select_related('organizer', 'customer').order_by('start_time')[:5]

    context = {
        'weeks': weeks,
        'month_label': f'{MONTH_NAMES[month]} {year}',
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'upcoming': upcoming,
    }
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'meetings/_calendar_results.html', context)
    return render(request, 'meetings/calendar.html', context)


@login_required
def meeting_detail_view(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    return render(request, 'meetings/meeting_detail.html', {'meeting': meeting})


@login_required
def meeting_create_view(request):
    if request.method == 'POST':
        attendee_ids = request.POST.getlist('attendees')
        date_str = request.POST['meeting_date']
        start_str = request.POST['start_time_only']
        end_str = request.POST['end_time_only']
        start_time = dt.fromisoformat(f'{date_str}T{start_str}')
        end_time = dt.fromisoformat(f'{date_str}T{end_str}')
        meeting = Meeting.objects.create(
            title=request.POST['title'],
            description=request.POST.get('description', ''),
            start_time=start_time,
            end_time=end_time,
            organizer_id=request.POST['organizer'],
            location=request.POST.get('location', ''),
            customer_id=request.POST.get('customer') or None,
            opportunity_id=request.POST.get('opportunity') or None,
        )
        meeting.attendees.set(attendee_ids)
        all_employee_ids = list(attendee_ids) + [str(meeting.organizer_id)]
        conflicts = check_leave_conflicts(
            meeting.start_time, meeting.end_time, all_employee_ids
        )
        if conflicts.exists():
            names = ', '.join(
                f'{conflict.employee.name} '
                f'({conflict.start_date}-{conflict.end_date})'
                for conflict in conflicts
            )
            messages.warning(
                request,
                f'Şu katılımcılar bu tarihlerde izinli görünüyor: {names}. '
                f'Toplantı yine de oluşturuldu.'
            )
        send_meeting_invites_task.delay(meeting.pk)
        return redirect('meeting-detail', pk=meeting.pk)

    from crm.models import Opportunity
    from sales.models import Customer

    return render(request, 'meetings/meeting_form.html', {
        'employees': Employee.objects.all(),
        'customers': Customer.objects.all(),
        'opportunities': Opportunity.objects.exclude(stage__in=['won', 'lost']),
    })


@login_required
def meeting_edit_view(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    if request.method == 'POST':
        date_str = request.POST['meeting_date']
        start_str = request.POST['start_time_only']
        end_str = request.POST['end_time_only']
        start_time = dt.fromisoformat(f'{date_str}T{start_str}')
        end_time = dt.fromisoformat(f'{date_str}T{end_str}')
        meeting.title = request.POST['title']
        meeting.description = request.POST.get('description', '')
        meeting.start_time = start_time
        meeting.end_time = end_time
        meeting.organizer_id = request.POST['organizer']
        meeting.location = request.POST.get('location', '')
        meeting.customer_id = request.POST.get('customer') or None
        meeting.opportunity_id = request.POST.get('opportunity') or None
        meeting.save()
        attendee_ids = request.POST.getlist('attendees')
        meeting.attendees.set(attendee_ids)
        all_employee_ids = list(attendee_ids) + [str(meeting.organizer_id)]
        conflicts = check_leave_conflicts(
            meeting.start_time, meeting.end_time, all_employee_ids
        )
        if conflicts.exists():
            names = ', '.join(
                f'{conflict.employee.name} '
                f'({conflict.start_date}-{conflict.end_date})'
                for conflict in conflicts
            )
            messages.warning(
                request,
                f'Şu katılımcılar bu tarihlerde izinli görünüyor: {names}. '
                f'Toplantı yine de oluşturuldu.'
            )
        return redirect('meeting-detail', pk=meeting.pk)

    from crm.models import Opportunity
    from sales.models import Customer

    return render(request, 'meetings/meeting_form.html', {
        'meeting': meeting,
        'employees': Employee.objects.all(),
        'customers': Customer.objects.all(),
        'opportunities': Opportunity.objects.exclude(stage__in=['won', 'lost']),
    })


@login_required
def check_conflicts_api(request):
    date_str = request.GET.get('date')
    start_str = request.GET.get('start_time')
    end_str = request.GET.get('end_time')
    employee_ids = request.GET.getlist('employee_ids')

    if not (date_str and start_str and end_str and employee_ids):
        return JsonResponse({'conflicts': []})

    try:
        start_time = dt.fromisoformat(f'{date_str}T{start_str}')
        end_time = dt.fromisoformat(f'{date_str}T{end_str}')
    except ValueError:
        return JsonResponse({'conflicts': []})

    conflicts = check_leave_conflicts(start_time, end_time, employee_ids)
    return JsonResponse({
        'conflicts': [
            f'{conflict.employee.name} '
            f'({conflict.start_date}-{conflict.end_date})'
            for conflict in conflicts
        ]
    })


@login_required
def meeting_cancel_view(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    if request.method == 'POST':
        meeting.status = Meeting.Status.CANCELLED
        meeting.save(update_fields=['status'])
    return redirect('meeting-detail', pk=meeting.pk)
