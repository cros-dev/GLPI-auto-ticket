"""
URLs da API de autenticação e SSPR.

Define rotas para:
- Autenticação: Geração de token de autenticação
- SSPR: Solicitação, validação e confirmação de reset de senha
"""
from django.urls import path
from rest_framework.authtoken import views as drf_authtoken_views
from .views import (
    PasswordResetRequestView,
    OtpValidationView,
    PasswordResetConfirmView
)

app_name = 'accounts'

urlpatterns = [
    # =========================================================
    # AUTENTICAÇÃO
    # =========================================================
    path('token/', drf_authtoken_views.obtain_auth_token, name='obtain-token'),
    
    # =========================================================
    # SSPR - Self-Service Password Reset
    # =========================================================
    path(
        'password-reset/request/',
        PasswordResetRequestView.as_view(),
        name='password-reset-request'
    ),
    path(
        'password-reset/validate-otp/',
        OtpValidationView.as_view(),
        name='password-reset-validate-otp'
    ),
    path(
        'password-reset/confirm/',
        PasswordResetConfirmView.as_view(),
        name='password-reset-confirm'
    ),
]
