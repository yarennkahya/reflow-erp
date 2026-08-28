def notifications_processor(request):
    if request.user.is_authenticated:
        qs = request.user.notifications.filter(is_read=False).order_by('-created_at')
        return {'nav_notifications': qs[:5], 'nav_notification_count': qs.count()}
    return {'nav_notifications': [], 'nav_notification_count': 0}
