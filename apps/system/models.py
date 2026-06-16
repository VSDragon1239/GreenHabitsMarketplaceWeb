from django.contrib.auth.models import User
from django.db import models


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    text = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True, help_text="Куда кликнуть, чтобы перейти")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Для {self.user.username}: {self.text}"
