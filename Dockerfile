FROM python:3.10-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Создание директорий
RUN mkdir -p /app/python /app/webapp /app/uploads /app/outputs \
    /var/log/nginx /var/log/python /var/log/supervisor \
    /run /var/run

# Копирование конфигурационных файлов (будут переопределены через volumes)
COPY config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY config/nginx.conf /etc/nginx/sites-available/default

# Включение сайта nginx
RUN ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default \
    && rm -f /etc/nginx/sites-enabled/default

# Копирование кода приложения (будет переопределено через volumes в development)
COPY python/ /app/python/
COPY webapp/ /app/webapp/

# Установка Python зависимостей
WORKDIR /app/python
COPY requirements.txt /app/python/
RUN pip install --no-cache-dir -r requirements.txt

# Экспозиция порта
EXPOSE 80

# Запуск supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
