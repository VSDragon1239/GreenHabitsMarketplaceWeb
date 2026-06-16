"""
URL configuration for MarketplaceGreenHabits project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView, LogoutView

from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from apps.about.views import IndexView
from apps.accounts.views import ProfileView, EditProfileView, PartnerDashboardView, PartnerOfferListView, \
    PartnerOfferCreateView, PartnerOfferUpdateView, PartnerOfferDeleteView, PartnerLoginView
from apps.administrations.views import AdminDashBoardView, AdminUserManagementView, AdminAuthRequestsUsersView, \
    ModerateRequestView, AdminCheckEcoTasksView, AdminCheckAiAntiFrodeEcoTasksView, AdminEcoTasksManageView, \
    AdminEcoTaskCreateView, AdminEcoTaskUpdateView, AdminEcoTaskDeleteView, ReviewTaskActionView, \
    AdminRunAIModerationView, AdminReportsView, AdminExportCSVView
from apps.marketplace.views import EcoTaskDetailsView, EcoTasksTrackerView, CompleteEcoTaskView, EcoBonusListView, \
    EditEcoBonusView, AddEcoBonusView, MarketplaceView, ExchangeOfferView
from apps.system.views import NoAccessView
from apps.trackers.views import EcoHabitsTrackerView, EcoHabitsCategoriesView, EcoHabitsView, EcoHabitDetailsView, \
    LogEcoHabitView

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.png')),

    path('', IndexView.as_view(), name="main"),
    path(
        'login/',
        PartnerLoginView.as_view(
            template_name="accounts/auth.html",
            redirect_authenticated_user=True,
            next_page="/profile/",
        ),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(
            next_page="/login/"
        ),
        name="logout",
    ),

    path('reset-password/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('reset-password/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # ============================================================
    #                      Администрирование
    # ============================================================
    path('no-access/', NoAccessView.as_view(), name="no-access"),
    path('admin/', RedirectView.as_view(url='panel/', permanent=True), name='admin_panel'),
    path('admin/panel/', admin.site.urls),
    path('admin-dashboard/', AdminDashBoardView.as_view(), name="admin_dashboard"),
    path('admin-auth-requests/', AdminAuthRequestsUsersView.as_view(), name="admin_registration_requests"),
    path('admin/users/', AdminUserManagementView.as_view(), name='admin_users_management'),
    path('api/moderate-request/<int:pk>/', ModerateRequestView.as_view(), name='api_moderate_request'),
    # Управляет кнопками для заявок на регистрацию
    path('admin/check/eco-tasks/', AdminCheckEcoTasksView.as_view(), name='admin_check_eco_tasks'),
    path('admin/check/eco-tasks-ai/', AdminCheckAiAntiFrodeEcoTasksView.as_view(),
         name='admin_check_ai_frode_eco_tasks'),

    path('admin/eco-tasks/', AdminEcoTasksManageView.as_view(), name='admin_eco_tasks_manage'),
    path('admin/eco-tasks/create/', AdminEcoTaskCreateView.as_view(), name='admin_eco_task_create'),
    path('admin/eco-tasks/<int:pk>/edit/', AdminEcoTaskUpdateView.as_view(), name='admin_eco_task_edit'),
    path('admin/eco-tasks/<int:pk>/delete/', AdminEcoTaskDeleteView.as_view(), name='admin_eco_task_delete'),

    # Внутри urlpatterns добавь:
    path('admin/reports/', AdminReportsView.as_view(), name='admin_reports'),
    path('admin/export/<str:model_name>/', AdminExportCSVView.as_view(), name='admin_export_csv'),

    # ============================================================
    #                      Пользователи
    # ============================================================
    path('contacts/', IndexView.as_view(), name="contacts"),
    path('profile/', ProfileView.as_view(), name='profile'),  # Профиль пользователя
    path('profile/edit/', EditProfileView.as_view(), name='profile_edit'),

    # ============================================================
    #                      Маркетплейс
    # ============================================================

    # Заменяем старый плейсхолдер маркетплейса на эти две строки:
    path('marketplace/', MarketplaceView.as_view(), name="marketplace"),
    path('marketplace/exchange/<int:pk>/', ExchangeOfferView.as_view(), name='marketplace_exchange'),
    path('moderation/tasks/<int:pk>/ai-run/', AdminRunAIModerationView.as_view(), name='admin_run_ai_moderation'),

    # --- ЗАДАЧИ ---
    path('eco-tasks-tracker/', EcoTasksTrackerView.as_view(), name='eco_tasks_tracker'),
    path('eco-task-details/<int:pk>/', EcoTaskDetailsView.as_view(), name='eco_task_details'),
    path('eco-tasks/complete/<int:task_id>/', CompleteEcoTaskView.as_view(), name='eco_task_complete'),
    path('admin/check/eco-tasks/<int:pk>/review/', ReviewTaskActionView.as_view(), name='review_task_action'),

    # --- ПРИВЫЧКИ ---
    path('eco-habits-tracker/', EcoHabitsTrackerView.as_view(), name='eco_habits_tracker'),
    path('eco-habits-categories/', EcoHabitsCategoriesView.as_view(), name='eco_habits_categories'),
    path('categories/<int:pk>/eco-habits/', EcoHabitsView.as_view(), name='eco_habits'),
    path('categories/<int:pk1>/eco-habits/<int:pk2>/details', EcoHabitDetailsView.as_view(), name='eco_habit_details'),
    path('eco-habits/log/<int:pk>/', LogEcoHabitView.as_view(), name='eco_habit_log'),

    # --- ПОЛУЧЕННЫЕ БОНУСЫ - --
    path('eco-bonus-list/', EcoBonusListView.as_view(), name='eco_bonus_list'),
    path('edit-eco-bonus/<int:pk>/', EditEcoBonusView.as_view(), name='edit_eco_bonus'),
    path('add-eco-bonus/', AddEcoBonusView.as_view(), name='add_eco_bonus'),

    # ============================================================
    #                      Спонсоры
    # ============================================================
    path('partner/dashboard/', PartnerDashboardView.as_view(), name='partner_dashboard'),
    path('partner/offers/', PartnerOfferListView.as_view(), name='partner_offers'),
    path('partner/offers/create/', PartnerOfferCreateView.as_view(), name='partner_offer_create'),
    path('partner/offers/<int:pk>/edit/', PartnerOfferUpdateView.as_view(), name='partner_offer_edit'),
    path('partner/offer/<int:pk>/delete/', PartnerOfferDeleteView.as_view(), name='partner_offer_delete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
