from django.contrib.auth.models import User
from django.db import models


class EcoHabitCategory(models.Model):
    """Категории: Вода, Энергия, Мусор и т.д."""
    name = models.CharField(max_length=100, verbose_name="Название категории")
    icon = models.CharField(max_length=50, default="bi-recycle", verbose_name="CSS класс иконки Bootstrap",
                            help_text="Например: bi-droplet, bi-lightning-charge")

    class Meta:
        verbose_name = "Категория привычки"
        verbose_name_plural = "Категории привычек"

    def __str__(self):
        return self.name


class EcoHabit(models.Model):
    """Сама привычка"""
    category = models.ForeignKey(EcoHabitCategory, on_delete=models.CASCADE, related_name="habits")
    title = models.CharField(max_length=255, verbose_name="Название привычки")
    description = models.TextField(verbose_name="Что нужно сделать")
    base_reward = models.IntegerField(default=5, verbose_name="Базовая награда (ECO)")
    streak_bonus = models.IntegerField(default=1, verbose_name="Бонус за день серии",
                                       help_text="+1 ECO за каждый день подряд")
    max_bonus = models.IntegerField(default=15, verbose_name="Максимальный бонус",
                                    help_text="Лимит бонуса (чтобы не раздуть экономику)")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        verbose_name = "Эко-привычка"
        verbose_name_plural = "Эко-привычки"

    def __str__(self):
        return self.title


class UserHabitLog(models.Model):
    """
    Лог выполнения привычек.
    Хранит дату и текущую длину серии на момент выполнения.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habit_logs")
    habit = models.ForeignKey(EcoHabit, on_delete=models.PROTECT, related_name="logs")
    date_completed = models.DateField(verbose_name="Дата выполнения")
    streak_count = models.IntegerField(default=1, verbose_name="Длина серии в этот день")
    reward_earned = models.IntegerField(verbose_name="Начислено монет")

    class Meta:
        verbose_name = "Лог привычки"
        verbose_name_plural = "Логи привычек"
        # Пользователь может отметить конкретную привычку только ОДИН раз в день
        unique_together = ['user', 'habit', 'date_completed']
        ordering = ['-date_completed']
