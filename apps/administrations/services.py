from django.contrib.auth.models import User, Group
from django.utils.crypto import get_random_string

from apps.accounts.models import Profile
from apps.system.email_sender import send_templated_mail


def process_registration_approval(request_obj):
    """Создает пользователя и отправляет письмо. Возвращает (True, пароль) или (False, ошибка)"""
    if request_obj.status == "approved":
        return False, "Заявка уже одобрена"

    email = request_obj.email
    if User.objects.filter(username=email).exists():
        return False, "Пользователь с таким email уже существует"

    # 1. Генерация и создание
    raw_password = get_random_string(length=12, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789')
    fio_parts = request_obj.fio.split()

    new_user = User.objects.create_user(
        username=email,
        email=email,
        password=raw_password,
        first_name=fio_parts[1] if len(fio_parts) > 1 else "",
        last_name=fio_parts[0] if fio_parts else "",
        is_active=True
    )
    Profile.objects.create(user=new_user)

    try:
        new_user.groups.add(Group.objects.get(name='Участники'))
    except Group.DoesNotExist:
        pass

    # 2. Отправка письма
    send_templated_mail(
        subject="Доступ к порталу Green ZabGu открыт",
        template_path="webuiprojectgreenzabgu/emails/registration_approved.html",
        context_dict={
            "fio": request_obj.fio, "username": email, "password": raw_password,
            "login_url": "https://localhost/login/"
        },
        to_email=email
    )

    # 3. Смена статуса
    request_obj.status = "approved"
    request_obj.save()

    return True, raw_password


def process_registration_rejection(request_obj):
    """Отклоняет заявку и отправляет уведомление на email. Возвращает (True, сообщение) или (False, ошибка)"""
    if request_obj.status == "rejected":
        return False, "Заявка уже отклонена"
    if request_obj.status == "approved":
        return False, "Нельзя отклонить уже одобренную заявку"

    # 1. Отправка письма об отказе
    send_templated_mail(
        subject="Заявка на регистрацию в Green ZabGu",
        template_path="webuiprojectgreenzabgu/emails/registration_rejected.html",
        context_dict={
            "fio": request_obj.fio
        },
        to_email=request_obj.email
    )

    # 2. Смена статуса
    request_obj.status = "rejected"
    request_obj.save()

    return True, "Заявка успешно отклонена"
