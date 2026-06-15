from django.db import models

class RegistrationRequestStatus(models.TextChoices):
    NEW = "new", "Новая"
    APPROVED = "approved", "Одобрена"
    REJECTED = "rejected", "Отклонена"


class RegistrationRequest(models.Model):
    """Таблица для хранения заявок с формы контактов"""
    fio = models.CharField(max_length=255, verbose_name="ФИО")
    group = models.CharField(max_length=100, verbose_name="Группа")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    email = models.EmailField(verbose_name="Email")

    # Полезные системные поля:
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания заявки")
    status = models.CharField(
        max_length=20,
        choices=RegistrationRequestStatus.choices,
        default=RegistrationRequestStatus.NEW,
        verbose_name="Статус заявки"
    )

    class Meta:
        verbose_name = "Заявка на регистрацию"
        verbose_name_plural = "Заявки на регистрацию"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.fio} ({self.group}) - {self.get_status_display()}"