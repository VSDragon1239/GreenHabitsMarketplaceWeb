from django.contrib import admin
from django.shortcuts import redirect
from django.utils.html import format_html
from django.db import transaction as db_transaction
from django.contrib import messages

from apps.ecowallet.services import EcoCoinService
from apps.ecowallet.models import EcoTransactionType
from apps.marketplace.models import (
    EcoTask, EcoTaskType, UserTaskCompletion,
    # EcoHabit, EcoHabitCategory,
    # Partner, Offer, UserPromoCode
)


# ==========================================================
# ЭКО-ЗАДАНИЯ И МОДЕРАЦИЯ
# ==========================================================

@admin.register(EcoTaskType)
class EcoTaskTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')


@admin.register(EcoTask)
class EcoTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'task_type', 'reward', 'is_active')
    list_filter = ('is_active', 'task_type')
    search_fields = ('title',)


@admin.register(UserTaskCompletion)
class UserTaskCompletionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'task', 'status_badge', 'created_at',
        'proof_preview', 'ai_feedback_short', 'admin_comment'
    )
    list_filter = ('status', 'task__task_type', 'task')
    search_fields = ('user__username', 'user__email', 'task__title')
    readonly_fields = ('user', 'task', 'created_at', 'proof_text', 'proof_image_full', 'ai_feedback')
    list_per_page = 30  # Пагинация для удобства

    # Запрещаем удаление, только смена статусов
    def has_delete_permission(self, request, obj=None):
        return False

    # --- UI Улучшения ---
    def status_badge(self, obj):
        colors = {
            'pending': 'bg-yellow-100 text-yellow-800',
            'ai_approved': 'bg-blue-100 text-blue-800',
            'ai_rejected': 'bg-orange-100 text-orange-800',
            'approved': 'bg-green-100 text-green-800',
            'rejected': 'bg-red-100 text-red-800',
            'cancelled': 'bg-gray-100 text-gray-800',
        }
        css_class = colors.get(obj.status, 'bg-gray-100')
        return format_html(
            '<span class="{} text-xs px-2 py-1 rounded-full font-semibold">{}</span>',
            css_class, obj.get_status_display()
        )

    status_badge.short_description = 'Статус'

    def proof_preview(self, obj):
        if obj.proof_image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" width="60" height="60" style="object-fit:cover; border-radius:8px;"/></a>',
                obj.proof_image.url, obj.proof_image.url
            )
        elif obj.proof_text:
            return format_html('<span class="text-gray-600 text-xs">{}</span>', obj.proof_text[:50])
        return "-"

    proof_preview.short_description = 'Доказательство'

    def proof_image_full(self, obj):
        if obj.proof_image:
            return format_html('<img src="{}" style="max-width:400px; border-radius:8px;"/>', obj.proof_image.url)
        return "Нет фото"

    proof_image_full.short_description = 'Полное фото'

    def ai_feedback_short(self, obj):
        if obj.ai_feedback:
            return format_html('<span class="text-xs text-purple-600">🤖 {}</span>', obj.ai_feedback[:50])
        return "-"

    ai_feedback_short.short_description = 'Вердикт ИИ'

    # --- Действия (Actions) ---
    @admin.action(description='✅ Одобрить и начислить ECO (Выбранные)')
    def approve_and_credit_coins(self, request, queryset):
        # Обрабатываем только те, что на модерации
        pending_qs = queryset.filter(status__in=['pending', 'ai_rejected', 'ai_approved'])
        success_count = 0

        for comp in pending_qs:
            try:
                with db_transaction.atomic():
                    EcoCoinService.credit(
                        user=comp.user,
                        amount=comp.task.reward,
                        tx_type=EcoTransactionType.TASK_COMPLETED,
                        external_id=f"task:{comp.task_id}:user:{comp.user_id}"
                    )
                    comp.status = 'approved'
                    comp.save(update_fields=['status', 'reviewed_at'])
                    success_count += 1
            except Exception as e:
                self.message_user(request, f"Ошибка у {comp.user.username}: {str(e)}", level=messages.ERROR)

        if success_count > 0:
            self.message_user(request, f"Успешно одобрено {success_count} заданий. Баллы начислены.",
                              level=messages.SUCCESS)

    @admin.action(description='❌ Отклонить задание (Баллы НЕ начисляются)')
    def reject_tasks(self, request, queryset):
        updated = queryset.filter(status__in=['pending', 'ai_rejected', 'ai_approved']).update(status='rejected')
        self.message_user(request, f"Отклонено {updated} заданий.", level=messages.SUCCESS)

    @admin.action(description='🚫 Отменить и списать ECO (Для уже одобренных мошенников)')
    def cancel_and_revoke_coins(self, request, queryset):
        # Для заданий со статусом approved, которые нужно откатить
        approved_qs = queryset.filter(status='approved')
        success_count = 0

        for comp in approved_qs:
            try:
                success, msg = EcoCoinService.reverse_task_completion(comp.user, comp)
                if success:
                    success_count += 1
            except Exception as e:
                self.message_user(request, f"Ошибка у {comp.user.username}: {str(e)}", level=messages.ERROR)

        if success_count > 0:
            self.message_user(request, f"Отменено {success_count} заданий. Монеты списаны.", level=messages.SUCCESS)

    actions = [approve_and_credit_coins, reject_tasks, cancel_and_revoke_coins]

    # --- Кнопки на странице редактирования одной записи ---
    change_form_template = "admin/user_task_completion_change_form.html"

    def response_change(self, request, obj):
        if "_approve_task" in request.POST:
            try:
                with db_transaction.atomic():
                    EcoCoinService.credit(
                        user=obj.user,
                        amount=obj.task.reward,
                        tx_type=EcoTransactionType.TASK_COMPLETED,
                        external_id=f"task:{obj.task_id}:user:{obj.user_id}"
                    )
                    obj.status = 'approved'
                    obj.save(update_fields=['status', 'reviewed_at'])
                self.message_user(request, f"Одобрено! +{obj.task.reward} ECO", level=messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Ошибка: {str(e)}", level=messages.ERROR)
            return redirect(".")

        if "_reject_task" in request.POST:
            obj.status = 'rejected'
            obj.save(update_fields=['status', 'reviewed_at'])
            self.message_user(request, "Задание отклонено.", level=messages.WARNING)
            return redirect(".")

        if "_cancel_task" in request.POST:
            try:
                success, msg = EcoCoinService.reverse_task_completion(obj.user, obj)
                if success:
                    self.message_user(request, msg, level=messages.SUCCESS)
                else:
                    self.message_user(request, msg, level=messages.WARNING)
            except Exception as e:
                self.message_user(request, f"Ошибка: {str(e)}", level=messages.ERROR)
            return redirect("..")

        return super().response_change(request, obj)

# # ==========================================================
# # ПРИВЫЧКИ И КАТЕГОРИИ
# # ==========================================================
# @admin.register(EcoHabitCategory)
# class EcoHabitCategoryAdmin(admin.ModelAdmin):
#     list_display = ('name', 'icon')
#
#
# @admin.register(EcoHabit)
# class EcoHabitAdmin(admin.ModelAdmin):
#     list_display = ('title', 'category', 'base_reward', 'streak_bonus', 'is_active')
#     list_filter = ('category', 'is_active')
#
#
# # ==========================================================
# # МАРКЕТПЛЕЙС И ПАРТНЕРЫ
# # ==========================================================
# @admin.register(Partner)
# class PartnerAdmin(admin.ModelAdmin):
#     list_display = ('name', 'get_user_display', 'get_total_offers', 'get_status_badge')
#     search_fields = ('name', 'user__username')
#     # ... (здесь остается твой старый код PartnerAdmin без изменений) ...
#     pass
#
#
# @admin.register(Offer)
# class OfferAdmin(admin.ModelAdmin):
#     list_display = ('title', 'partner', 'category', 'price_in_eco', 'is_active')
#     list_filter = ('partner', 'category', 'is_active')
#     list_editable = ('is_active',)
#
#
# @admin.register(UserPromoCode)
# class UserPromoCodeAdmin(admin.ModelAdmin):
#     list_display = ('code', 'user', 'offer', 'is_used', 'created_at')
#     list_filter = ('is_used', 'offer__partner')
#     readonly_fields = ('code', 'created_at')
