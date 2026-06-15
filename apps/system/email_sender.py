from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_templated_mail(subject, template_path, context_dict, to_email):
    """
    Универсальная функция отправки HTML-письма.
    """
    # Рендерим HTML из шаблона
    html_content = render_to_string(template_path, context_dict)

    # Формируем письмо
    msg = EmailMultiAlternatives(
        subject=subject,
        body="",  # Текстовая версия пустая (сейчас все читают HTML)
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    msg.attach_alternative(html_content, "text/html")

    # Отправляем (fail_silently=False означает, что при ошибке Django покажет её в логах)
    msg.send(fail_silently=False)
