from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView
from django.db import transaction as db_transaction
from django.contrib import messages

from apps.accounts.forms import UserEditForm, ProfileAvatarForm
from apps.accounts.models import Profile
from apps.accounts.permissions import RoleRequiredMixin
from apps.ecowallet.models import EcoCoinTransaction
from apps.ecowallet.services import EcoCoinService
from apps.marketplace.models import UserTaskCompletion
from apps.trackers.models import UserHabitLog


class ProfileView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    required_roles = ["Участники", "Руководители", "Администраторы", "Контент менеджер"]
    login_url = "/login/"  # куда перенаправлять
    redirect_field_name = "next"  # параметр с origin
    template_name = "accounts/profile.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user

        # БЕЗОПАСНОЕ получение профиля
        profile, _ = Profile.objects.get_or_create(user=user)
        context['profile'] = profile

        # Баланс
        eco_balance = EcoCoinService.get_balance(user)
        context['eco_balance'] = eco_balance

        # --- НОВОЕ: Геймификация (Уровень и прогресс) ---
        # Простая формула: 1 уровень = 100 ECO. Можно усложнить потом.
        context['level'] = (eco_balance // 100) + 1
        context['progress_percent'] = eco_balance % 100

        # --- НОВОЕ: Статистика ---
        context['completed_tasks_count'] = UserTaskCompletion.objects.filter(user=user).count()

        # Считаем максимальную серию из логов привычек
        max_streak = UserHabitLog.objects.filter(user=user).aggregate(max_streak=Max('streak_count'))['max_streak']
        context['max_streak'] = max_streak if max_streak else 0

        # --- НОВОЕ: Последняя активность (из транзакций) ---
        # Берем 5 последних транзакций для ленты
        context['recent_transactions'] = EcoCoinTransaction.objects.filter(
            wallet__user=user
        ).order_by('-created_at')[:5]

        # Выполненные задания (если нужны где-то еще)
        context['completed_tasks'] = UserTaskCompletion.objects.filter(
            user=user
        ).select_related('task').order_by('-completed_at')

        # Роли
        roles_priority = {
            'Администраторы': ('Администратор', 'danger'),
            'Контент менеджер': ('Контент-менеджер', 'info'),
            'Руководители': ('Руководитель', 'warning'),
            'Участники': ('Участник', 'secondary'),
        }
        user_groups = user.groups.values_list('name', flat=True)
        context['display_role'] = ('Без роли', 'light')

        for group_name in user_groups:
            if group_name in roles_priority:
                context['display_role'] = roles_priority[group_name]
                break

        return context


class EditProfileView(LoginRequiredMixin, View):
    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        u_form = UserEditForm(instance=request.user)
        p_form = ProfileAvatarForm(instance=profile)

        context = {
            'u_form': u_form,
            'p_form': p_form,
        }
        return render(request, 'accounts/profile_edit.html', context)

    def post(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)

        u_form = UserEditForm(request.POST, instance=request.user)
        # ВАЖНО: request.FILES для аватарки!
        p_form = ProfileAvatarForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            with db_transaction.atomic():
                u_form.save()
                p_form.save()
            messages.success(request, 'Ваши данные успешно обновлены!')
            return redirect('profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')

        context = {
            'u_form': u_form,
            'p_form': p_form,
        }
        return render(request, 'accounts/profile_edit.html', context)
