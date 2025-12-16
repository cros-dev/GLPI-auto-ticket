from pathlib import Path
import os

# =========================================================
# CARREGAMENTO DO .env
# =========================================================

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
except Exception:
    # Se python-dotenv não estiver instalado,
    # seguimos apenas com variáveis de ambiente do sistema
    pass


# =========================================================
# BASE DIR
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# SEGURANÇA BÁSICA
# =========================================================

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('DJANGO_SECRET_KEY não definido')

DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',')
    if h.strip()
]

# Fallback seguro para desenvolvimento
if not ALLOWED_HOSTS and DEBUG:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# =========================================================
# APPLICATION DEFINITION
# =========================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceiros
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',

    # Apps locais
    'accounts',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Deve estar antes de CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# =========================================================
# BANCO DE DADOS
# =========================================================

POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'db')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

if all([POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD]):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': POSTGRES_DB,
            'USER': POSTGRES_USER,
            'PASSWORD': POSTGRES_PASSWORD,
            'HOST': POSTGRES_HOST,
            'PORT': POSTGRES_PORT,
        }
    }
else:
    db_name = os.getenv('DJANGO_DB_NAME', 'db.sqlite3')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / db_name,
        }
    }


# =========================================================
# VALIDAÇÃO DE SENHA
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =========================================================
# INTERNACIONALIZAÇÃO
# =========================================================

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Manaus'
USE_I18N = True
USE_TZ = True


# =========================================================
# ARQUIVOS ESTÁTICOS
# =========================================================

STATIC_URL = os.getenv('DJANGO_STATIC_URL', 'static/')


# =========================================================
# SEGURANÇA EM PRODUÇÃO (NGINX / HTTPS)
# =========================================================

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# =========================================================
# INTEGRAÇÕES EXTERNAS
# =========================================================

# GLPI API v2.1 (futuro)
GLPI_API_URL = os.getenv('GLPI_API_URL')
GLPI_API_TOKEN = os.getenv('GLPI_API_TOKEN')
GLPI_BASE_URL = os.getenv('GLPI_BASE_URL')

# GLPI API Legacy
GLPI_LEGACY_API_URL = os.getenv('GLPI_LEGACY_API_URL')
GLPI_LEGACY_API_USER = os.getenv('GLPI_LEGACY_API_USER')
GLPI_LEGACY_API_PASSWORD = os.getenv('GLPI_LEGACY_API_PASSWORD')
GLPI_LEGACY_APP_TOKEN = os.getenv('GLPI_LEGACY_APP_TOKEN')

# n8n
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL')

# IA - Google Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


# =========================================================
# DJANGO REST FRAMEWORK
# =========================================================

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}


# =========================================================
# LOGGING (simples e útil em Docker)
# =========================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}


# =========================================================
# CORS (Para Frontend Angular)
# =========================================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",  # Angular dev server padrão
]

# Permitir credenciais (cookies, auth headers)
CORS_ALLOW_CREDENTIALS = True

# Headers permitidos
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]


# =========================================================
# DEFAULT FIELD
# =========================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
