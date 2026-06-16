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

from django.db.models import Sum, Max


class ProfileView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    required_roles = ["Участники", "Руководители", "Администраторы", "Контент менеджер", "Партнёры"]
    login_url = "/login/"
    redirect_field_name = "next"
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

        # Текущий баланс (для покупок)
        eco_balance = EcoCoinService.get_balance(user)
        context['eco_balance'] = eco_balance

        # --- НОВОЕ: Геймификация (Уровень считается от ВСЕГО заработанного) ---
        # Суммируем только положительные транзакции (начисления)
        total_earned = EcoCoinTransaction.objects.filter(
            wallet__user=user,
            amount__gt=0
        ).aggregate(total=Sum('amount'))['total'] or 0

        context['level'] = (total_earned // 100) + 1
        context['progress_percent'] = total_earned % 100
        context['total_earned'] = total_earned  # На всякий случай, если захочешь вывести

        # --- Статистика ---
        context['completed_tasks_count'] = UserTaskCompletion.objects.filter(
            user=user, status='approved'
        ).count()

        max_streak = UserHabitLog.objects.filter(user=user).aggregate(max_streak=Max('streak_count'))['max_streak']
        context['max_streak'] = max_streak if max_streak else 0

        # Последняя активность
        context['recent_transactions'] = EcoCoinTransaction.objects.filter(
            wallet__user=user
        ).order_by('-created_at')[:5]

        context['completed_tasks'] = UserTaskCompletion.objects.filter(
            user=user
        ).select_related('task').order_by('reviewed_at')

        # --- НОВОЕ: Роли с Tailwind CSS классами ---
        roles_priority = {
            'Администраторы': ('Администратор', 'bg-red-500 text-white'),
            'Контент менеджер': ('Контент-менеджер', 'bg-blue-500 text-white'),
            'Руководители': ('Руководитель', 'bg-yellow-500 text-white'),
            'Партнёры': ('Партнёр', 'bg-purple-500 text-white'),
            'Участники': ('Участник', 'bg-green-500 text-white'),
        }
        user_groups = user.groups.values_list('name', flat=True)
        context['display_role'] = ('Без роли', 'bg-gray-400 text-white')

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
