from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from dashboard.views_helpers import paginate

from .models import Notification


@login_required
@require_GET
def notification_list_view(request):
    notifications = request.user.notifications.order_by('-created_at')
    page_obj = paginate(request, notifications)
    return render(request, 'notifications/list.html', {
        'page_obj': page_obj,
        'notifications': page_obj,
        'unread_count': request.user.notifications.filter(is_read=False).count(),
    })


@login_required
@require_GET
def notification_feed_view(request):
    notifications = request.user.notifications.filter(is_read=False).order_by('-created_at')
    unread_count = notifications.count()
    return JsonResponse({
        'count': unread_count,
        'html': render_to_string('notifications/_dropdown_items.html', {
            'nav_notifications': notifications[:5],
            'nav_notification_count': unread_count,
        }, request=request),
    })


@login_required
@require_POST
def notification_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'count': request.user.notifications.filter(is_read=False).count(),
            'redirect_url': notification.url,
        })
    return redirect(notification.url or 'notification-list')
