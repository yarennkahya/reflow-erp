import calendar as pycal
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from hr.models import Employee

from .models import Meeting
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
        meeting = Meeting.objects.create(
            title=request.POST['title'],
            description=request.POST.get('description', ''),
            start_time=request.POST['start_time'],
            end_time=request.POST['end_time'],
            organizer_id=request.POST['organizer'],
            location=request.POST.get('location', ''),
            customer_id=request.POST.get('customer') or None,
            opportunity_id=request.POST.get('opportunity') or None,
        )
        meeting.attendees.set(attendee_ids)
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
        meeting.title = request.POST['title']
        meeting.description = request.POST.get('description', '')
        meeting.start_time = request.POST['start_time']
        meeting.end_time = request.POST['end_time']
        meeting.organizer_id = request.POST['organizer']
        meeting.location = request.POST.get('location', '')
        meeting.customer_id = request.POST.get('customer') or None
        meeting.opportunity_id = request.POST.get('opportunity') or None
        meeting.save()
        attendee_ids = request.POST.getlist('attendees')
        meeting.attendees.set(attendee_ids)
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
def meeting_cancel_view(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    if request.method == 'POST':
        meeting.status = Meeting.Status.CANCELLED
        meeting.save(update_fields=['status'])
    return redirect('meeting-detail', pk=meeting.pk)
