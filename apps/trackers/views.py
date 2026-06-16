from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import get_object_or_404
from django.http import Http404

from apps.ecowallet.models import EcoTransactionType
from apps.ecowallet.services import EcoCoinService
from apps.trackers.models import EcoHabitCategory, UserHabitLog, EcoHabit


# Create your views here.
class EcoHabitsTrackerView(LoginRequiredMixin, TemplateView):
    """
    Теперь это не пустая страница, а Главный Дашборд Привычек.
    Отсюда пользователь идет к категориям.
    """
    template_name = "webuiprojectgreenzabgu/ecohabits/eco_habits_tracker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Получаем все категории, в которых есть привычки
        context['categories'] = EcoHabitCategory.objects.filter(habits__is_active=True).distinct()

        # Считаем общую статистику для карточек на дашборде
        from django.db.models import Max, Count
        stats = UserHabitLog.objects.filter(user=user).aggregate(
            total_logs=Count('id'),
            max_streak=Max('streak_count')
        )
        context['total_habits_done'] = stats['total_logs'] or 0
        context['best_streak'] = stats['max_streak'] or 0

        return context


class MarkHabitDoneView(LoginRequiredMixin, View):  # LoginRequiredMixin гарантирует,
    # что метод сработает только для авторизованных пользователей
    def post(self, request, habit_id):
        try:
            # external_id формируем так: habit:5:user:2 (чтобы за один день за одну привычку дать коины 1 раз)
            ext_id = f"habit:{habit_id}:user:{request.user.id}:date:{datetime.now().strftime('%Y-%m-%d')}"

            new_balance = EcoCoinService.credit(
                user=request.user,
                amount=5,
                tx_type=EcoTransactionType.HABIT_TRACKED,
                external_id=ext_id
            )
            return JsonResponse({"status": "success", "new_balance": str(new_balance)})

        except Exception as e:
            # Если попытка дублирования (UniqueConstraint) или другая ошибка
            return JsonResponse({"status": "error", "message": str(e)}, status=400)


class EcoHabitsCategoriesView(LoginRequiredMixin, ListView):
    """Страница выбора категории привычек"""
    model = EcoHabitCategory
    template_name = "webuiprojectgreenzabgu/ecohabits/eco_habits_categories.html"
    context_object_name = 'categories'

    def get_queryset(self):
        # Скрываем категории, в которых нет ни одной активной привычки
        return EcoHabitCategory.objects.filter(habits__is_active=True).distinct()


class EcoHabitsView(LoginRequiredMixin, ListView):
    """Список привычек внутри конкретной категории"""
    model = EcoHabit
    template_name = "webuiprojectgreenzabgu/ecohabits/eco_habits.html"
    context_object_name = 'habits'

    def get_queryset(self):
        # Получаем категории из URL (pk)
        category_id = self.kwargs.get('pk')
        return EcoHabit.objects.filter(is_active=True, category_id=category_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(EcoHabitCategory, pk=self.kwargs.get('pk'))

        # Получаем сегодняшние серии для всех привычек разом (оптимизация запросов)
        today = timezone.localdate()
        logs_today = UserHabitLog.objects.filter(
            user=self.request.user,
            date_completed=today,
            habit__in=context['habits']
        ).values_list('habit_id', flat=True)

        context['completed_today_ids'] = set(logs_today)
        return context


class EcoHabitDetailsView(LoginRequiredMixin, DetailView):
    """Детальная страница привычки с инфой о серии"""
    model = EcoHabit
    template_name = "webuiprojectgreenzabgu/ecohabits/eco_habit_details.html"
    context_object_name = 'habit'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        # Берем pk2 из URL (категория нам здесь для загрузки объекта не нужна)
        pk = self.kwargs.get('pk2')
        queryset = queryset.filter(pk=pk)

        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404("Привычка не найдена")

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Отмечено ли сегодня?
        today = timezone.localdate()
        context['is_completed_today'] = UserHabitLog.objects.filter(
            user=user, habit=self.object, date_completed=today
        ).exists()

        # Текущая серия (берем самый свежий лог)
        last_log = UserHabitLog.objects.filter(user=user, habit=self.object).first()
        context['current_streak'] = last_log.streak_count if last_log else 0

        return context


class LogEcoHabitView(LoginRequiredMixin, View):
    """AJAX обработчик нажатия кнопки 'Отметить'"""

    def post(self, request, pk):
        habit = get_object_or_404(EcoHabit, pk=pk, is_active=True)

        try:
            result = EcoCoinService.log_habit_and_credit(request.user, habit)

            streak_text = f"Серия: {result['streak']} дн.!"
            if result['is_new_streak'] and result['streak'] % 7 == 0:
                streak_text += " 🔥 Неделя!"

            return JsonResponse({
                "status": "success",
                "message": f"+{result['reward']} ECO. {streak_text}",
                "new_balance": str(result['balance']),
                "new_streak": result['streak']
            })

        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Habit Log Error: {str(e)}", exc_info=True)
            return JsonResponse({"error": "Ошибка сервера"}, status=500)
