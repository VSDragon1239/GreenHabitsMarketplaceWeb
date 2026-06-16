from apps.system.models import Notification


def user_notifications(request):
    if request.user.is_authenticated:
        return {
            'unread_notifications': Notification.objects.filter(user=request.user, is_read=False)[:5],
            'unread_notifications_count': Notification.objects.filter(user=request.user, is_read=False).count()
        }
    return {}
