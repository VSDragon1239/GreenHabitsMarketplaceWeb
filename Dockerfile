#FROM python:3.11-slim
FROM mirror.gcr.io/library/python:3.11-slim
LABEL authors="VariableStarryDragon"

# Установим системные зависимости (PostgreSQL client, gcc для сборки psycopg2 и т.п.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    build-essential libpq-dev postgresql-client \
  && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Копируем и даём права entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=MainWebUIProject.settings

# Собираем статику
RUN python manage.py collectstatic --noinput

# Создаём папку для media и даём право записи
RUN mkdir -p /app/media \
    && chown -R www-data:www-data /app/media

# Открываем порт для Django
EXPOSE 8000

# Команда запуска (gunicorn лучше указывать timeout и количество воркеров по нагрузке)
# При старте сначала entrypoint, потом gunicorn
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "mysite.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
