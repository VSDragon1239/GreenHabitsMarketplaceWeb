from datetime import timedelta

from django.db import transaction as db_transaction
from django.db.models import F
from django.utils import timezone

from apps.ecowallet.models import EcoWallet, EcoCoinTransaction, EcoTransactionType
from apps.trackers.models import UserHabitLog


class InsufficientFundsError(Exception):
    pass


class EcoCoinService:
    @staticmethod
    def get_balance(user) -> int:
        """Быстрое получение баланса без блокировок (для отображения в UI)"""
        wallet = getattr(user, 'eco_wallet', None)
        if wallet:
            return wallet.balance
        return 0

    @staticmethod
    @db_transaction.atomic
    def process_transaction(user, amount: int, tx_type: str, external_id: str = None):
        amount = int(amount)
        if amount == 0:
            return

        # Блокируем строку кошелька в Postgres
        wallet, _ = EcoWallet.objects.select_for_update().get_or_create(
            user=user,
            defaults={'balance': 0}
        )

        if amount < 0 and wallet.balance < abs(amount):
            raise InsufficientFundsError("Недостаточно эко-коинов")

        # F() защищает от Race Conditions (конкурентных запросов)
        wallet.balance = F('balance') + amount
        wallet.save(update_fields=['balance'])

        EcoCoinTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            tx_type=tx_type,
            external_id=external_id
        )
        wallet.refresh_from_db(fields=['balance'])
        return wallet.balance

    @staticmethod
    def credit(user, amount: int, tx_type: str, external_id: str = None):
        return EcoCoinService.process_transaction(user, abs(amount), tx_type, external_id)

    @staticmethod
    def debit(user, amount: int, tx_type: str, external_id: str = None):
        return EcoCoinService.process_transaction(user, -abs(amount), tx_type, external_id)

    @staticmethod
    @db_transaction.atomic
    def log_habit_and_credit(user, habit):
        today = timezone.localdate()

        # external_id формируется так, чтобы сработал UniqueConstraint из модели EcoCoinTransaction
        external_id = f"habit:{habit.id}:user:{user.id}:date:{today}"

        # 1. Проверяем, не отмечал ли уже сегодня (на уровне БД лога)
        if UserHabitLog.objects.filter(user=user, habit=habit, date_completed=today).exists():
            raise ValueError("Привычка уже отмечена сегодня")

        # 2. Считаем серию (Streak)
        yesterday = today - timedelta(days=1)
        last_log = UserHabitLog.objects.filter(
            user=user,
            habit=habit,
            date_completed__lte=yesterday  # Ищем в прошлом
        ).order_by('-date_completed').first()

        if last_log and last_log.date_completed == yesterday:
            # Если отмечал вчера — серия продолжается
            current_streak = last_log.streak_count + 1
        else:
            # Если вчера не отмечал (или вообще никогда) — серия сбрасывается на 1
            current_streak = 1

        # 3. Считаем награду (Базовая + Бонус, но не больше МаксБонуса)
        calculated_bonus = min(current_streak * habit.streak_bonus, habit.max_bonus)
        total_reward = habit.base_reward + calculated_bonus

        # 4. Начисляем монеты через наш надежный сервис
        new_balance = EcoCoinService.credit(
            user=user,
            amount=total_reward,
            tx_type=EcoTransactionType.HABIT_TRACKED,
            external_id=external_id
        )

        # 5. Сохраняем лог серии
        UserHabitLog.objects.create(
            user=user,
            habit=habit,
            date_completed=today,
            streak_count=current_streak,
            reward_earned=total_reward
        )

        return {
            "balance": new_balance,
            "streak": current_streak,
            "reward": total_reward,
            "is_new_streak": current_streak > 1
        }

    @staticmethod
    @db_transaction.atomic
    def reverse_task_completion(user, completion_obj):
        """Безопасная отмена выполнения задания и списание монет."""
        # 1. Проверка, не отменено ли уже
        if completion_obj.status == 'cancelled':
            return False, "Задание уже было отменено ранее"

        amount_to_deduct = completion_obj.task.reward

        # 2. Блокируем кошелек
        wallet = EcoWallet.objects.select_for_update().get(user=user)

        # 3. Создаем транзакцию отмены (с минусом)
        EcoCoinTransaction.objects.create(
            wallet=wallet,
            amount=-amount_to_deduct,
            tx_type=EcoTransactionType.TASK_REVERSED,
            external_id=f"reversed_task:{completion_obj.task.id}:user:{user.id}"
        )

        # 4. Обновляем баланс (разрешаем уход в минус при отмене,
        # чтобы админ всегда мог откатить мошеннические начисления)
        wallet.balance = F('balance') - amount_to_deduct
        wallet.save(update_fields=['balance'])

        # 5. Меняем статус задания
        completion_obj.status = 'cancelled'
        completion_obj.save(update_fields=['status'])

        wallet.refresh_from_db(fields=['balance'])
        return True, f"Успешно. Списано {amount_to_deduct} ECO. Баланс стал: {wallet.balance}"
