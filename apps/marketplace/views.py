import logging
import uuid
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import DetailView
from django.db import transaction as db_transaction, IntegrityError
from django.shortcuts import get_object_or_404

from django.views import View

from apps.ecowallet.models import EcoCoinTransaction, EcoTransactionType
from apps.ecowallet.services import EcoCoinService
from apps.marketplace.models import EcoTask, UserTaskCompletion

logger = logging.getLogger(__name__)


class EcoTaskDetailsView(LoginRequiredMixin,
                         DetailView):  # DetailView от Django — он сам найдет задачу в БД по ID из URL или выдаст красивую ошибку 404, если задача не существует.
    """Детальная страница конкретного задания"""
    model = EcoTask
    template_name = "marketplace/tasks/eco_task_details.html"
    context_object_name = 'task'  # В шаблоне объект будет доступен как {{ task }}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Проверяем, выполнил ли текущий пользователь ЭТУ задачу
        is_completed = UserTaskCompletion.objects.filter(
            user=self.request.user,
            task=self.object
        ).exists()

        context['is_completed'] = is_completed
        return context


class CompleteEcoTaskView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        task = get_object_or_404(EcoTask, pk=task_id, is_active=True)

        task_type_code = task.task_type.code if task.task_type else 'trust'

        proof_text = ""
        proof_image = None

        # 1. Валидация типа задания
        if task_type_code == 'text_code':
            proof_text = request.POST.get('proof_text', '').strip()
            if not proof_text:
                return JsonResponse({"error": "Введите код для подтверждения"}, status=400)

            if task.secret_code and proof_text.upper() != task.secret_code.upper():
                return JsonResponse(
                    {"error": "Неверный код! Проверьте данные и попробуйте снова."},
                    status=400,
                )

        elif task_type_code == 'photo':
            if 'proof_image' not in request.FILES:
                return JsonResponse({"error": "Прикрепите фотографию"}, status=400)
            proof_image = request.FILES['proof_image']

        # 2. Проверка: не было ли уже выполнения этой задачи пользователем
        if UserTaskCompletion.objects.filter(user=request.user, task=task).exists():
            return JsonResponse({"error": "Вы уже выполнили это задание"}, status=400)

        # 3. Создаём выполнение со статусом PENDING (баллы НЕ начисляем!)
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
                "message": "Задание отправлено на проверку. Баллы будут начислены после модерации.",
            })

        except IntegrityError as e:
            error_msg = str(e)
            logger.warning(f"IntegrityError в CompleteEcoTaskView: {error_msg}")

            # Смотрим, что именно упало: по уникальному индексу user+task
            task_already_done = UserTaskCompletion.objects.filter(
                user=request.user, task=task
            ).exists()
            if task_already_done:
                return JsonResponse(
                    {"error": "Вы уже отправляли это задание на проверку"}, status=400
                )

            return JsonResponse(
                {"error": f"Ошибка базы данных (IntegrityError): {error_msg}"},
                status=400,
            )

        except Exception as e:
            logger.error(f"Critical error completing task {task_id}: {str(e)}", exc_info=True)
            return JsonResponse({"error": f"Ошибка сервера: {str(e)}"}, status=500)
