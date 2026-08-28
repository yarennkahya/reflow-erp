from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notification


@login_required
def notification_list_view(request):
    notifications = request.user.notifications.order_by('-created_at')
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
def notification_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return redirect(notification.url or 'notification-list')
