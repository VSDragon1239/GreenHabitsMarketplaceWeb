import logging
import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import DetailView, TemplateView
from django.db import transaction as db_transaction, IntegrityError
from django.shortcuts import get_object_or_404

from django.views import View

from apps.ecowallet.models import EcoTransactionType
from apps.ecowallet.services import EcoCoinService
from apps.marketplace.models import EcoTask, UserTaskCompletion, Offer, UserPromoCode

logger = logging.getLogger(__name__)


class EcoTasksTrackerView(LoginRequiredMixin, TemplateView):
    template_name = "marketplace/tasks/eco_tasks_tracker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. Доступные (невыполненные) задания
        # Исключаем те, что уже на проверке или одобрены. Если отклонены (rejected) - можно пересдать
        submitted_ids = UserTaskCompletion.objects.filter(
            user=user
        ).exclude(status__in=['rejected', 'cancelled']).values_list('task_id', flat=True)

        available_tasks = EcoTask.objects.filter(is_active=True).exclude(pk__in=submitted_ids)

        context['tasks'] = available_tasks
        context['active_tasks_count'] = available_tasks.count()

        # 2. Задания, которые сейчас висят на модерации
        context['pending_tasks'] = UserTaskCompletion.objects.filter(
            user=user,
            status__in=['pending', 'ai_approved', 'ai_rejected']
        ).select_related('task').order_by('-created_at')

        # 3. Последние 5 выполненных (одобренных)
        context['recent_completions'] = UserTaskCompletion.objects.filter(
            user=user,
            status='approved'
        ).select_related('task').order_by('-reviewed_at')[:5]

        # 4. Статистика
        context['total_completed'] = UserTaskCompletion.objects.filter(
            user=user, status='approved'
        ).count()

        return context


class EcoTaskDetailsView(LoginRequiredMixin, DetailView):
    """Детальная страница конкретного задания"""
    model = EcoTask
    template_name = "marketplace/tasks/eco_task_details.html"
    context_object_name = 'task'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Ищем активную попытку сдачи (исключаем отклоненные и отмененные)
        completion = UserTaskCompletion.objects.filter(
            user=self.request.user,
            task=self.object
        ).exclude(status__in=['rejected', 'cancelled']).first()

        if completion:
            context['is_pending'] = True
            context['completion_status'] = completion.status
            context['ai_feedback'] = completion.ai_feedback
        else:
            context['is_pending'] = False

        return context


class CompleteEcoTaskView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        task = get_object_or_404(EcoTask, pk=task_id, is_active=True)
        task_type_code = task.task_type.code if task.task_type else 'trust'

        proof_text = ""
        proof_image = None

        if task_type_code == 'text_code':
            proof_text = request.POST.get('proof_text', '').strip()
            if not proof_text:
                return JsonResponse({"error": "Введите код для подтверждения"}, status=400)
            if task.secret_code and proof_text.upper() != task.secret_code.upper():
                return JsonResponse({"error": "Неверный код! Проверьте данные и попробуйте снова."}, status=400)

        elif task_type_code == 'photo':
            if 'proof_image' not in request.FILES:
                return JsonResponse({"error": "Прикрепите фотографию"}, status=400)
            proof_image = request.FILES['proof_image']

        # Проверка: не висит ли уже задание на проверке или не выполнено ли оно
        if UserTaskCompletion.objects.filter(
                user=request.user, task=task
        ).exclude(status__in=['rejected', 'cancelled']).exists():
            return JsonResponse({"error": "Вы уже отправили это задание или оно на проверке"}, status=400)

        try:
            with db_transaction.atomic():
                UserTaskCompletion.objects.create(
                    user=request.user,
                    task=task,
                    proof_text=proof_text,
                    proof_image=proof_image,
                    status=UserTaskCompletion.Status.PENDING,
                )

            return JsonResponse({
                "status": "success",
                "message": "Задание отправлено на проверку!",
                "new_balance": str(EcoCoinService.get_balance(request.user))
                # Возвращаем текущий баланс (он не изменился)
            })

        except IntegrityError as e:
            logger.warning(f"IntegrityError в CompleteEcoTaskView: {str(e)}")
            return JsonResponse({"error": "Вы уже отправляли это задание на проверку"}, status=400)

        except Exception as e:
            logger.error(f"Critical error completing task {task_id}: {str(e)}", exc_info=True)
            return JsonResponse({"error": f"Ошибка сервера: {str(e)}"}, status=500)


class EcoBonusListView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/eco_bonus_list.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EditEcoBonusView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/edit_eco_bonus.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class AddEcoBonusView(TemplateView):
    template_name = "webuiprojectgreenzabgu/pages/add_eco_bonus.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class MarketplaceView(LoginRequiredMixin, TemplateView):
    """Главная страница маркетплейса"""
    template_name = "marketplace/marketplace.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Получаем все активные предложения
        context['offers'] = Offer.objects.filter(is_active=True).select_related('partner')
        # Получаем промокоды текущего пользователя
        context['user_promocodes'] = UserPromoCode.objects.filter(
            user=self.request.user
        ).select_related('offer', 'offer__partner').order_by('-created_at')
        return context


class ExchangeOfferView(LoginRequiredMixin, View):
    """AJAX View для обмена ECO на промокод"""

    def post(self, request, pk):
        offer = get_object_or_404(Offer, pk=pk, is_active=True)
        user = request.user

        # 1. Пытаемся списать баллы (EcoCoinService.debit кинет ошибку, если баллов не хватает)
        try:
            EcoCoinService.debit(
                user=user,
                amount=offer.price_in_eco,
                tx_type=EcoTransactionType.MARKETPLACE_PURCHASE,
                external_id=f"offer:{offer.id}:user:{user.id}"
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

        # 2. Генерируем уникальный промокод
        promo_code = f"ECO-{uuid.uuid4().hex[:8].upper()}"

        # 3. Создаём запись в БД
        UserPromoCode.objects.create(
            user=user,
            offer=offer,
            code=promo_code
        )

        # 4. Возвращаем успех и новый баланс
        return JsonResponse({
            "success": True,
            "promo_code": promo_code,
            "new_balance": str(EcoCoinService.get_balance(user))
        })
