"""
URLs da API de autenticação.

Define rotas para autenticação e obtenção de tokens:
- Token: Geração de token de autenticação para API REST
"""
from django.urls import path
from rest_framework.authtoken import views as drf_authtoken_views

app_name = 'accounts'

urlpatterns = [
    # =========================================================
    # AUTENTICAÇÃO
    # =========================================================
    path('token/', drf_authtoken_views.obtain_auth_token, name='obtain-token'),
]
