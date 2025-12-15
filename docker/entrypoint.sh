#!/bin/bash
set -e

# =========================================================
# Garante execução no diretório do Django
# =========================================================
cd /app

# =========================================================
# Executa migrações
# =========================================================
python manage.py migrate --noinput

# =========================================================
# Cria superuser automaticamente (se configurado)
# =========================================================
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
python << 'EOF'
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f'Superuser criado: {username}')
else:
    print(f'Superuser já existe: {username}')
EOF
fi

# =========================================================
# Executa o comando principal (gunicorn, runserver, etc)
# =========================================================
exec "$@"
