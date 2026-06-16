from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")

    def __str__(self):
        return self.user.get_username()

class Partner(models.Model):
    """Спонсор/Партнер (бизнес-сущность)"""
    name = models.CharField(max_length=255, verbose_name="Название партнера")
    icon = models.CharField(max_length=50, default="store", verbose_name="Иконка Material Icons")

    # ПРЯМАЯ СВЯЗЬ: Кто управляет этим бизнесом?
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_partner",
        verbose_name="Управляющий аккаунт"
    )

    class Meta:
        verbose_name = "Партнер"
        verbose_name_plural = "Партнеры"

    def __str__(self):
        return self.name


