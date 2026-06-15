# WebUiProject/context_processors.py
# Чтобы не менять get_context_data в каждой вьюхе (IndexView, ProfileView и т.д.)
from .services import EcoCoinService


def eco_balance(request):
    """
    Добавляет переменную {{ user_eco_balance }} во все шаблоны.
    """
    balance = "0.0000"
    if request.user.is_authenticated:
        # select_related здесь не нужен, так как мы обращаемся через кэш или прямым getattr
        balance = EcoCoinService.get_balance(request.user)
    return {'user_eco_balance': balance}

# Подключите его в settings.py:
# Найдите блок TEMPLATES и добавьте путь к процессору в context_processors:
# 'WebUiProject.context_processors.eco_balance',
