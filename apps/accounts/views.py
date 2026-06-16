from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Max, Count, Q
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, UpdateView, DeleteView, CreateView, ListView
from django.db import transaction as db_transaction
from django.contrib import messages

from apps.accounts.forms import UserEditForm, ProfileAvatarForm, OfferCreateForm
from apps.accounts.models import Profile
from apps.accounts.permissions import RoleRequiredMixin
from apps.ecowallet.models import EcoCoinTransaction
from apps.ecowallet.services import EcoCoinService
from apps.marketplace.models import UserTaskCompletion, Offer, UserPromoCode
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


class PartnerDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "accounts/partner_dashboard.html"
    required_roles = ['Партнеры']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # БЕЗОПАСНОЕ получение партнера (если админ добавил в группу, но не привязал бизнес)
        partner = getattr(self.request.user, 'managed_partner', None)

        # Если партнер не привязан, показываем заглушку
        if not partner:
            context['setup_required'] = True
            return context

        # Агрегация статистики по офферам текущего партнера
        offers_stats = UserPromoCode.objects.filter(offer__partner=partner).aggregate(
            total_issued=Count('id'),
            total_used=Count('id', filter=Q(is_used=True))
        )

        # Считаем уникальных клиентов (у которых есть хотя бы 1 не использованный промокод)
        active_clients = UserPromoCode.objects.filter(
            offer__partner=partner,
            is_used=False
        ).values('user').distinct().count()

        context['partner'] = partner
        context['total_issued'] = offers_stats['total_issued'] or 0
        context['total_used'] = offers_stats['total_used'] or 0
        context['active_clients'] = active_clients

        # Последние 3 промокода для отображения на дашборде
        context['recent_promos'] = Offer.objects.filter(partner=partner).order_by('-id')[:3]

        return context


class PartnerOfferListView(RoleRequiredMixin, ListView):
    template_name = "accounts/partner_offers.html"
    required_roles = ['Партнеры']
    context_object_name = 'offers'

    def get_queryset(self):
        # Используем безопасное получение
        partner = getattr(self.request.user, 'managed_partner', None)
        if not partner:
            # Если партнер не привязан, возвращаем пустой queryset
            return Offer.objects.none()
        return Offer.objects.filter(partner=partner).order_by('-id')


class PartnerOfferCreateView(RoleRequiredMixin, CreateView):
    template_name = "accounts/partner_create_offer.html"
    required_roles = ['Партнеры']
    form_class = OfferCreateForm
    model = Offer
    success_url = reverse_lazy('partner_offers')

    def form_valid(self, form):
        partner = getattr(self.request.user, 'managed_partner', None)
        if not partner:
            messages.error(self.request, "Ваш аккаунт не привязан к профилю партнера. Обратитесь к администратору.")
            return redirect('no-access')

        form.instance.partner = partner
        form.instance.is_active = True
        messages.success(self.request, "Предложение успешно создано!")
        return super().form_valid(form)


class PartnerOfferUpdateView(RoleRequiredMixin, UpdateView):
    template_name = "accounts/partner_offer_edit.html"
    required_roles = ['Партнеры']
    form_class = OfferCreateForm
    model = Offer

    # Переопределяем URL, так как нам нужно передать pk в URL
    def get_success_url(self):
        return reverse_lazy('partner_offers')

    def get_object(self, queryset=None):
        # Находим оффер по ID из URL
        offer = get_object_or_404(Offer, pk=self.kwargs.get('pk'))

        # БЕЗОПАСНОСТЬ: Проверяем, что этот оффер принадлежит текущему партнеру
        if offer.partner != self.request.user.managed_partner:
            # Если попытка взломать URL напрямую, кидаем на 403 (No-access)
            raise PermissionDenied("Вы можете редактировать только свои предложения")

        return offer

    def form_valid(self, form):
        # На случай, если кто-то подделает HTML-форму и попытается отправить чужой ID
        form.instance.partner = self.request.user.managed_partner
        messages.success(self.request, "Предложение успешно обновлено!")
        return super().form_valid(form)


class PartnerOfferDeleteView(RoleRequiredMixin, DeleteView):
    template_name = "accounts/partner_offer_delete.html"
    model = Offer  # Наследуем от UpdateView, чтобы получить доступ к объекту
    context_object_name = 'offer'

    def get_success_url(self):
        return reverse_lazy('partner_offers')

    def get_object(self, queryset=None):
        offer = get_object_or_404(Offer, pk=self.kwargs.get('pk'))

        if offer.partner != self.request.user.managed_partner:
            raise Http404("Объект не найден")
        return offer

    def delete(self, request, *args, **kwargs):
        # Доп. проверка через Post (на случай прямого вызова POST)
        self.object = self.get_object()
        partner = self.object.partner

        # Формируем сообщение для шаблона
        self.extra_context = {
            'object_name': self.object.title,
            'partner_name': partner.name
        }

        return super().delete(request, *args, **kwargs)


# apps/accounts/views.py
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy


class PartnerLoginView(LoginView):
    """Кастомный логин, который редиректит партнёров сразу на их дашборд"""

    def get_success_url(self):
        user = self.request.user
        # Проверяем, состоит ли пользователь в группе "Партнеры"
        if user.is_authenticated and user.groups.filter(name='Партнеры').exists():
            return reverse_lazy('partner_dashboard')
        # Остальные идут на главную страницу (или куда укажешь)
        return reverse_lazy('profile')
