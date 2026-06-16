from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, ListView

from .forms import AdminUserForm
from .models import RegistrationRequest
from .services import process_registration_approval, process_registration_rejection
from ..accounts.models import Profile, Partner
from ..accounts.permissions import RoleRequiredMixin
from ..ecowallet.models import EcoWallet
from ..ecowallet.services import EcoCoinService
from ..marketplace.models import UserTaskCompletion


class AdminDashBoardView(TemplateView):
    template_name = "administrations/admin_dashboard.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class AdminAuthRequestsUsersView(RoleRequiredMixin, TemplateView):
    required_roles = ['Администраторы']
    template_name = "administrations/admin_registration_requests.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Группы (для фильтрации)
        leaders_group = Group.objects.get(name='Руководители')
        managers_group = Group.objects.get(name='Контент менеджер')
        members_group = Group.objects.get(name='Участники')

        # Пользователи по категориям
        context["leaders"] = User.objects.filter(groups=leaders_group)
        context["managers"] = User.objects.filter(groups=managers_group)
        context["members"] = User.objects.filter(groups=members_group)

        # Все пользователи (для быстрого поиска)
        context["users"] = User.objects.all()

        # НОВОЕ: Запросы на регистрацию (сначала новые)
        context["requests"] = RegistrationRequest.objects.all().order_by('-created_at')

        # НОВОЕ: Статистика в цифрах
        counts = RegistrationRequest.objects.values('status').annotate(count=Count('id'))
        stats_dict = {item['status']: item['count'] for item in counts}

        context["stats"] = {
            "new": stats_dict.get('new', 0),
            "approved": stats_dict.get('approved', 0),
            "rejected": stats_dict.get('rejected', 0),
            "total": sum(stats_dict.values())
        }

        return context


# Управляет заявками
class ModerateRequestView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            req = RegistrationRequest.objects.get(pk=pk)
        except RegistrationRequest.DoesNotExist:
            return JsonResponse({"error": "Заявка не найдена"}, status=404)

        action = request.POST.get("action")

        if action == "approve":
            success, result = process_registration_approval(req)
            if success:
                return JsonResponse({"status": "success", "message": "Пользователь создан, пароль отправлен"})
            else:
                return JsonResponse({"status": "error", "message": result}, status=400)


        elif action == "reject":
            success, result = process_registration_rejection(req)
            if success:
                return JsonResponse({"status": "success", "message": result})
            else:
                return JsonResponse({"status": "error", "message": result}, status=400)
        return JsonResponse({"error": "Неверный action"}, status=400)


class AdminUserManagementView(RoleRequiredMixin, View):
    required_roles = ['Администраторы']
    template_name = 'administrations/admin_users_management.html'

    def get(self, request):
        users = User.objects.select_related('profile', 'eco_wallet') \
            .prefetch_related('groups', 'managed_partner') \
            .all()

        context = {
            'users': users,
            'all_groups': Group.objects.all(),
            'registration_requests': RegistrationRequest.objects.filter(
                status='new'
            ).select_related() if hasattr(self, '_get_requests') else [],
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')

        if action == 'create':
            return self._create_user(request)
        elif action == 'edit':
            return self._update_user(request)
        elif action == 'delete':
            return self._delete_user(request)

        return JsonResponse({'error': 'Неизвестное действие'}, status=400)

    def _create_user(self, request):
        form = AdminUserForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    password = form.cleaned_data.get('password')
                    user.set_password(password if password else User.objects.make_random_password(length=12))
                    user.save()
                    form.save_m2m()

                    Profile.objects.create(
                        user=user,
                        phone=form.cleaned_data['phone'],
                        description=form.cleaned_data['description']
                    )
                    EcoWallet.objects.create(user=user, balance=0)

                    # ── Партнёр ──
                    self._handle_partner(request, user)

                return JsonResponse({'success': True, 'message': f'Пользователь {user.username} создан'})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        return JsonResponse({'error': form.errors}, status=400)

    def _update_user(self, request):
        user_id = request.POST.get('user_id')
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Пользователь не найден'}, status=404)

        form = AdminUserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    password = form.cleaned_data.get('password')
                    if password:
                        user.set_password(password)
                    user.save()
                    form.save_m2m()

                    # Profile — get_or_create вместо user.profile
                    # (автосозданный суперпользователь не имеет Profile)
                    profile, _ = Profile.objects.get_or_create(user=user)
                    profile.phone = form.cleaned_data['phone']
                    profile.description = form.cleaned_data['description']
                    if 'avatar' in request.FILES:
                        profile.avatar = request.FILES['avatar']
                    profile.save()

                    # ── Партнёр ──
                    self._handle_partner(request, user)

                return JsonResponse({'success': True, 'message': f'Данные {user.username} обновлены'})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        return JsonResponse({'error': form.errors}, status=400)

    def _delete_user(self, request):
        user_id = request.POST.get('user_id')
        try:
            user_to_delete = User.objects.select_related('eco_wallet').get(pk=user_id)

            if request.user == user_to_delete:
                return JsonResponse({'error': 'Вы не можете удалить свой аккаунт'}, status=403)

            if user_to_delete.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
                return JsonResponse({'error': 'Нельзя удалить последнего администратора системы'}, status=403)

            username = user_to_delete.username
            user_to_delete.delete()
            return JsonResponse({'success': True, 'message': f'Пользователь {username} удален'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'Пользователь не найден'}, status=404)

    # ──────────────────────────────────────────────────────────
    #  Обработка галочки «Партнёр» и названия организации
    # ──────────────────────────────────────────────────────────
    def _handle_partner(self, request, user):
        is_partner = 'is_partner' in request.POST
        partner_name = request.POST.get('partner_name', '').strip()

        if is_partner and partner_name:
            # Создаём или обновляем Partner, привязанный к user
            Partner.objects.update_or_create(
                user=user,
                defaults={'name': partner_name}
            )
            # Добавляем в группу «Партнёры»
            partners_group, _ = Group.objects.get_or_create(name='Партнёры')
            user.groups.add(partners_group)

        elif is_partner and not partner_name:
            # Галочка стоит, но название пустое — ничего не делаем,
            # валидация на фронте не пустит, но подстраховка
            pass

        else:
            # Галочка снята — отвязываем Partner от пользователя
            # (сам Partner остаётся в БД, но без управляющего)
            Partner.objects.filter(user=user).update(user=None)


class AdminCheckEcoTasksView(RoleRequiredMixin, ListView):
    template_name = "administrations/admin_check_eco_tasks.html"
    required_roles = ['Администраторы']

    model = UserTaskCompletion
    context_object_name = 'completions'
    paginate_by = 20

    def get_queryset(self):
        # Оптимизируем запросы и сортируем: сначала на ручной проверке, потом ИИ отклонения
        qs = super().get_queryset().select_related('user', 'task').order_by('created_at')

        status_filter = self.request.GET.get('status', 'pending')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = UserTaskCompletion.Status.choices
        context['current_status'] = self.request.GET.get('status', 'pending')
        return context


class AdminCheckAiAntiFrodeEcoTasksView(TemplateView):
    template_name = "administrations/admin_check_ai_frode_eco_tasks.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class ReviewTaskActionView(RoleRequiredMixin, View):
    """AJAX View для одобрения или отклонения"""
    required_roles = ['Администраторы']

    @transaction.atomic
    def post(self, request, pk):
        completion = get_object_or_404(UserTaskCompletion, pk=pk)
        action = request.POST.get('action')  # 'approve' или 'reject'
        comment = request.POST.get('comment', '')

        if completion.status in [UserTaskCompletion.Status.APPROVED, UserTaskCompletion.Status.CANCELLED]:
            return JsonResponse({'success': False, 'error': 'Задание уже обработано'}, status=400)

        if action == 'approve':
            # Начисляем баллы через сервис
            try:
                EcoCoinService.credit(
                    user=completion.user,
                    amount=completion.task.reward,
                    tx_type='TASK_REWARD',
                    external_id=f'task:{completion.id}'
                )
                completion.status = UserTaskCompletion.Status.APPROVED
                completion.admin_comment = comment
                completion.save()
                return JsonResponse({'success': True, 'message': f'Одобрено. +{completion.task.reward} ECO'})

            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)

        elif action == 'reject':
            completion.status = UserTaskCompletion.Status.REJECTED
            completion.admin_comment = comment
            completion.save()
            return JsonResponse({'success': True, 'message': 'Отклонено'})

        return JsonResponse({'success': False, 'error': 'Неизвестное действие'}, status=400)
