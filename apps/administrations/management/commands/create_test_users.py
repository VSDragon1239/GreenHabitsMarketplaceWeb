"""
Создание тестовых пользователей и партнёров.
Запуск: python manage.py create_test_users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

from apps.accounts.models import Profile, Partner
from apps.ecowallet.models import EcoWallet


class Command(BaseCommand):
    help = 'Создаёт 10 тестовых пользователей и 10 тестовых партнёров (ЗабГУ/Чита/Экология)'

    def handle(self, *args, **options):
        # Группы
        participants_group, _ = Group.objects.get_or_create(name='Участники')
        partners_group, _ = Group.objects.get_or_create(name='Партнёры')

        # ── Обычные пользователи ──
        regular_users = [
            ('Иван', 'Петров', 'ivan.petrov@example.com', '+79243801542'),
            ('Анна', 'Сидорова', 'anna.sidorova@example.com', '+79243809811'),
            ('Дмитрий', 'Кузнецов', 'dmitry.kuznetsov@example.com', '+79243804365'),
            ('Мария', 'Попова', 'maria.popova@example.com', '+79243802719'),
            ('Сергей', 'Смирнов', 'sergey.smirnov@example.com', '+79243807403'),
            ('Елена', 'Васильева', 'elena.vasilieva@example.com', '+79243805582'),
            ('Алексей', 'Федоров', 'alexey.fedorov@example.com', '+79243803194'),
            ('Ольга', 'Соколова', 'olga.sokolova@example.com', '+79243806257'),
            ('Михаил', 'Новиков', 'mikhail.novikov@example.com', '+79243808940'),
            ('Татьяна', 'Морозова', 'tatyana.morozova@example.com', '+79243802036'),
        ]

        self.stdout.write('\n📋 Создание обычных пользователей...')
        for first_name, last_name, email, phone in regular_users:
            if User.objects.filter(username=email).exists():
                self.stdout.write(f'  ⏭️  {email} — уже существует')
                continue

            user = User.objects.create_user(
                username=email,
                email=email,
                password='StarVanya1239PassWord',
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )
            Profile.objects.get_or_create(user=user, defaults={'phone': phone})
            EcoWallet.objects.get_or_create(user=user, defaults={'balance': 0})
            user.groups.add(participants_group)

            self.stdout.write(self.style.SUCCESS(f'  ✅ {first_name} {last_name} ({email})'))

        # ── Партнёры (связанные с Читой/ЗабГУ/экологией) ──
        partner_data = [
            ('Александр', 'Волков', 'volkov.partner@bk.ru', '+79145404412',
             'Эко-Кафе «Забайкалье»', 'restaurant'),

            ('Екатерина', 'Козлова', 'kozlova.biz@bk.ru', '+79145408853',
             'Книжный магазин «Политех» (ЗабГУ)', 'menu_book'),

            ('Андрей', 'Лебедев', 'lebedev.corp@bk.ru', '+79145401296',
             'Велопрокат «Чита-Трек»', 'pedal_bike'),

            ('Наталья', 'Козлова', 'n.kozlova@bk.ru', '+79145407731',
             'Столовая ЗабГУ', 'local_dining'),

            ('Игорь', 'Павлов', 'pavlov.media@bk.ru', '+79145403504',
             'Эко-отель «Ингода»', 'hotel'),

            ('Юлия', 'Семенова', 'semenova.job@bk.ru', '+79145406128',
             'Центр экологических инициатив Забайкалья', 'eco'),

            ('Никита', 'Степанов', 'stepanov.trade@bk.ru', '+79145409947',
             'Типография «Зелёный Лист»', 'print'),

            ('Светлана', 'Николаева', 'nikolaeva.pro@bk.ru', '+79145402265',
             'Магазин «Байкал-Эко»', 'shopping_bag'),

            ('Роман', 'Макаров', 'makarov.invest@bk.ru', '+79145405019',
             'Студия «Переработка-Чита»', 'recycling'),

            ('Ирина', 'Орлова', 'orlova.partner@bk.ru', '+79145407380',
             'Турбаза «Чикой»', 'cabin'),
        ]

        self.stdout.write('\n🤝 Создание пользователей-партнёров...')
        for first_name, last_name, email, phone, partner_name, icon in partner_data:
            if User.objects.filter(username=email).exists():
                self.stdout.write(f'  ⏭️  {email} — уже существует')
                continue

            user = User.objects.create_user(
                username=email,
                email=email,
                password='StarVanya1239PassWord',
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )
            Profile.objects.get_or_create(user=user, defaults={'phone': phone})
            EcoWallet.objects.get_or_create(user=user, defaults={'balance': 0})
            user.groups.add(partners_group)

            # Создание Partner и привязка к пользователю
            Partner.objects.get_or_create(
                name=partner_name,
                defaults={
                    'icon': icon,
                    'user': user,
                }
            )

            self.stdout.write(self.style.SUCCESS(
                f'  ✅ {first_name} {last_name} → «{partner_name}»'
            ))

        self.stdout.write(self.style.SUCCESS('\n🎉 Готово! Создано пользователей: 10 + партнёров: 10'))
        self.stdout.write('🔑 Пароль для всех: TestPass123!\n')
