import os
import uuid

from django.contrib.auth.models import User
from django.db import models

from apps.accounts.models import Partner


class EcoTaskType(models.Model):
    """Типы проверки заданий"""
    code = models.SlugField(unique=True, verbose_name="Код типа")
    name = models.CharField(max_length=100, verbose_name="Название")

    class Meta:
        verbose_name = "Тип проверки задания"
        verbose_name_plural = "Типы проверок заданий"

    def __str__(self):
        return self.name


# Функция для загрузки фото-доказательств
def task_proof_image_upload_to(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    name = uuid.uuid4().hex
    return os.path.join('tasks_proofs', f"{name}.{ext}")


class EcoTask(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название задания")
    description = models.TextField(blank=True, verbose_name="Описание")
    reward = models.IntegerField(default=10, verbose_name="Награда (ECO)")

    task_type = models.ForeignKey(
        EcoTaskType, on_delete=models.SET_NULL, null=True, verbose_name="Способ проверки"
    )

    # НОВОЕ: Поле для правильного ответа
    secret_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Секретный код (если тип 'Ввод текста')",
        help_text="Если заполнено, пользователь должен ввести ровно этот код. Сравнение без учета регистра."
    )

    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "Эко-задание"
        verbose_name_plural = "Эко-задания"

    def __str__(self):
        return f"{self.title} (+{self.reward} ECO)"


class UserTaskCompletion(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'На проверке'
        AI_APPROVED = 'ai_approved', 'Одобрено ИИ'
        AI_REJECTED = 'ai_rejected', 'Отклонено ИИ (На ручной проверке)'
        APPROVED = 'approved', 'Одобрено (Баллы начислены)'
        REJECTED = 'rejected', 'Отклонено'
        CANCELLED = 'cancelled', 'Отменено (Списание)'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="completed_tasks")
    task = models.ForeignKey('EcoTask', on_delete=models.CASCADE)

    proof_text = models.CharField('Текстовое доказательство', max_length=500, blank=True)
    proof_image = models.ImageField('Фото доказательство', upload_to='tasks_proofs/', blank=True)

    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    ai_feedback = models.TextField('Комментарий ИИ', blank=True, null=True,
                                   help_text="Что ответил ИИ при проверке")
    admin_comment = models.TextField('Комментарий админа', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'task'],
                condition=models.Q(status__in=['pending', 'ai_approved', 'ai_rejected', 'approved']),
                name='unique_active_task_completion'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.task.title} [{self.status}]"


class OfferCategory(models.TextChoices):
    FOOD = "Еда"
    SHOPS = "Магазины"
    SERVICES = "Услуги"
    MERCH = "Мерч"


class Offer(models.Model):
    """Конкретное предложение (Скидка 10% на обеды за 500 монет)"""
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="offers")
    title = models.CharField(max_length=255, verbose_name="Название оффера")
    description = models.TextField(verbose_name="Описание")
    price_in_eco = models.IntegerField(verbose_name="Цена в ECO-коинах")
    category = models.CharField(max_length=50, choices=OfferCategory.choices, verbose_name="Категория")
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "Предложение"
        verbose_name_plural = "Предложения маркетплейса"

    def __str__(self):
        return f"{self.title} ({self.price_in_eco} ECO)"


class UserPromoCode(models.Model):
    """Выданный пользователю промокод"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="promo_codes")
    offer = models.ForeignKey(Offer, on_delete=models.PROTECT, related_name="issued_codes")
    code = models.CharField(max_length=20, unique=True, verbose_name="Код промокода")
    is_used = models.BooleanField(default=False, verbose_name="Использован")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Промокод пользователя"
        verbose_name_plural = "Промокоды пользователей"

    def __str__(self):
        return f"{self.code} ({'Использован' if self.is_used else 'Активен'})"
