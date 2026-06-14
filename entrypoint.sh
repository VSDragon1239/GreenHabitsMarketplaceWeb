#!/bin/sh
set -e

# Ждём, пока Postgres не примет соединение
echo "⏳ Жду Postgres на $DATABASE_HOST:$DATABASE_PORT..."
until PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$POSTGRES_DB" -c '\q'; do
  echo "  Postgres недоступен, сплю 2 секунды…"
  sleep 2
done
echo "✅ Postgres готов!"

# Сначала собираем статику и применяем миграции
python manage.py collectstatic --noinput
python manage.py migrate --noinput


if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
  echo "🚀 Создаю суперпользователя ${DJANGO_SUPERUSER_USERNAME} (если ещё нет)…"
  python manage.py createsuperuser --noinput \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "$DJANGO_SUPERUSER_EMAIL" || true
fi



# Запускаем основной процесс
exec "$@"

