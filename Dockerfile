FROM python:3.12-slim

# Install system dependencies (removed php-fpm as it's not needed)
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY webapp/ /app/

# Install Python dependencies (removed sglang - using external API)
RUN pip install --no-cache-dir \
    torch==2.10.0 \
    torchvision==0.25.0 \
    transformers==4.57.1 \
    Pillow==12.1.1 \
    matplotlib==3.10.8 \
    einops==0.8.2 \
    addict==2.4.0 \
    easydict==1.13 \
    pymupdf==1.27.2.2 \
    psutil==7.2.2 \
    flask \
    flask-cors \
    requests

# Configure Nginx for static files and API proxying (removed PHP-FPM configuration)
RUN printf '%s\\n' \
    'server {' \
    '    listen 80;' \
    '    server_name localhost;' \
    '    root /app/templates;' \
    '    index index.html;' \
    '' \
    '    client_max_body_size 500M;' \
    '' \
    '    location / {' \
    '        try_files $uri $uri/ /index.html;' \
    '    }' \
    '' \
    '    location /api/ {' \
    '        proxy_pass http://127.0.0.1:5000/api/;' \
    '        proxy_set_header Host $host;' \
    '        proxy_set_header X-Real-IP $remote_addr;' \
    '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
    '        proxy_connect_timeout 600s;' \
    '        proxy_send_timeout 600s;' \
    '        proxy_read_timeout 600s;' \
    '    }' \
    '' \
    '    location /uploads/ {' \
    '        alias /app/uploads/;' \
    '    }' \
    '' \
    '    location /outputs/ {' \
    '        alias /app/outputs/;' \
    '    }' \
    '}' > /etc/nginx/sites-available/default

# Create Supervisor config using printf for reliability (removed php-fpm program)
RUN printf '%s\\n' \
    '[supervisord]' \
    'nodaemon=true' \
    '' \
    '[program:nginx]' \
    'command=/usr/sbin/nginx -g "daemon off;"' \
    'autostart=true' \
    'autorestart=true' \
    'stderr_logfile=/var/log/nginx/error.log' \
    'stdout_logfile=/var/log/nginx/access.log' \
    '' \
    '[program:python-backend]' \
    'command=python /app/python/app.py' \
    'directory=/app' \
    'autostart=true' \
    'autorestart=true' \
    'stderr_logfile=/var/log/python/error.log' \
    'stdout_logfile=/var/log/python/access.log' \
    'environment=PYTHONUNBUFFERED="1"' > /etc/supervisor/conf.d/supervisord.conf

# Create necessary directories with proper permissions (removed php-fpm log directory)
RUN mkdir -p /app/uploads /app/outputs /var/log/nginx /var/log/python && \
    chmod -R 777 /app/uploads /app/outputs /var/log/nginx /var/log/python

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
