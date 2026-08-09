FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    php-fpm \
    php-cli \
    php-curl \
    php-json \
    supervisor \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY webapp/ /app/

# Install Python dependencies
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
    sglang \
    kernels==0.11.7 \
    flask \
    flask-cors

# Configure PHP-FPM
RUN sed -i 's/;cgi.fix_pathinfo=1/cgi.fix_pathinfo=0/g' /etc/php/*/fpm/php.ini && \
    sed -i 's/listen = \/run\/php\/php.*-fpm.sock/listen = 9000/g' /etc/php/*/fpm/pool.d/www.conf

# Create Nginx config using printf to avoid heredoc issues
RUN printf '%s\n' \
    'server {' \
    '    listen 80;' \
    '    server_name localhost;' \
    '    root /app/templates;' \
    '    index index.php index.html;' \
    '' \
    '    client_max_body_size 500M;' \
    '' \
    '    location / {' \
    '        try_files $uri $uri/ /index.php?$query_string;' \
    '    }' \
    '' \
    '    location ~ \\.php$ {' \
    '        include fastcgi_params;' \
    '        fastcgi_pass 127.0.0.1:9000;' \
    '        fastcgi_index index.php;' \
    '        fastcgi_param SCRIPT_FILENAME /app/templates$fastcgi_script_name;' \
    '        fastcgi_buffer_size 128k;' \
    '        fastcgi_buffers 4 256k;' \
    '        fastcgi_busy_buffers_size 256k;' \
    '    }' \
    '' \
    '    location /api/ {' \
    '        proxy_pass http://127.0.0.1:5000/;' \
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

# Create Supervisor config
RUN echo '[supervisord]
nodaemon=true

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
stderr_logfile=/var/log/nginx/error.log
stdout_logfile=/var/log/nginx/access.log

[program:php-fpm]
command=/usr/sbin/php-fpm -F
autostart=true
autorestart=true
stderr_logfile=/var/log/php-fpm/error.log
stdout_logfile=/var/log/php-fpm/access.log

[program:python-backend]
command=python /app/python/app.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/python/error.log
stdout_logfile=/var/log/python/access.log
environment=PYTHONUNBUFFERED="1"' > /etc/supervisor/conf.d/supervisord.conf

# Create necessary directories with proper permissions
RUN mkdir -p /app/uploads /app/outputs /var/log/nginx /var/log/php-fpm /var/log/python && \
    chmod -R 777 /app/uploads /app/outputs /var/log/nginx /var/log/php-fpm /var/log/python

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
