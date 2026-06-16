from django.db import models
from django.contrib.auth.models import User


class EcoWallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="eco_wallet",
        verbose_name="Владелец"
    )
    # ВАЖНО: Integer, так как это баллы, а не дубли с копейками!
    balance = models.IntegerField(
        default=0,
        verbose_name="Текущий баланс"
    )

    class Meta:
        verbose_name = "Кошелек эко-коинов"
        verbose_name_plural = "Кошельки эко-коинов"

    def __str__(self):
        return f"Кошелек: {self.user.username} ({self.balance} ECO)"


class EcoTransactionType(models.TextChoices):
    # Начисления

    PROJECT_CREATED = "project_created", "Создание проекта"
    BLOG_PUBLISHED = "blog_published", "Публикация статьи"
    DAILY_BONUS = "daily_bonus", "Ежедневный бонус"
    MANUAL_REWARD = "manual_reward", "Ручное начисление (админом)"
    # Списания
    MARKETPLACE_PURCHASE = 'marketplace_purchase', 'Покупка на маркетплейсе'
    # SHOP_PURCHASE = "shop_purchase", "Покупка в магазине"
    TASK_REVERSED = "task_reversed", "Отмена эко-задачи (списание)"
    # Переводы
    TRANSFER_OUT = "transfer_out", "Перевод другому"
    TRANSFER_IN = "transfer_in", "Перевод от другого"
    TASK_COMPLETED = "task_completed", "Выполнение эко-задачи"
    HABIT_TRACKED = "habit_tracked", "Отметка эко-привычки"


class EcoCoinTransaction(models.Model):
    """
    Журнал операций (Ledger). Никогда не изменяйте записи в этой таблице (только CREATE).
    """
    wallet = models.ForeignKey(
        EcoWallet,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="Кошелек"
    )
    amount = models.IntegerField(
        verbose_name="Сумма (целое число)"
    )
    tx_type = models.CharField(
        max_length=30,
        choices=EcoTransactionType.choices,
        verbose_name="Тип операции"
    )
    # Идемпотентность: позволяет не дать баллы дважды за одно действие
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ID связанной сущности",
        help_text="Например: 'blog:15' или 'project:42'"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата операции")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Транзакция эко-коинов"
        verbose_name_plural = "Транзакции эко-коинов"
        # Защита от дублей на уровне БД
        constraints = [
            models.UniqueConstraint(
                fields=['wallet', 'tx_type', 'external_id'],
                condition=models.Q(external_id__isnull=False),
                name='unique_eco_transaction_for_entity'
            )
        ]

    def __str__(self):
        sign = "+" if self.amount > 0 else ""
        return f"{self.wallet.user.username}: {sign}{self.amount} ({self.get_tx_type_display()})"
