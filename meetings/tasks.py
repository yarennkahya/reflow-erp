from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_meeting_invites_task(meeting_id):
    from .models import Meeting

    try:
        meeting = Meeting.objects.select_related('organizer', 'customer').get(pk=meeting_id)
    except Meeting.DoesNotExist:
        return

    recipients = set()
    if meeting.organizer.email:
        recipients.add(meeting.organizer.email)
    for attendee in meeting.attendees.all():
        if attendee.email:
            recipients.add(attendee.email)
    if meeting.customer and meeting.customer.contact_email:
        recipients.add(meeting.customer.contact_email)

    if not recipients:
        return

    send_mail(
        subject=f'Toplantı Daveti: {meeting.title}',
        message=(
            f'{meeting.title}\n'
            f'Tarih: {meeting.start_time:%d %B %Y %H:%M}\n'
            f'Konum: {meeting.location or "Belirtilmedi"}\n'
            f'Organizatör: {meeting.organizer.name}\n\n'
            f'{meeting.description}'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=list(recipients),
        fail_silently=True,
    )
