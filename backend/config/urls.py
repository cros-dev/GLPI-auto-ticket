"""
URLs principais do projeto Django.

Define as rotas principais incluindo:
- Admin do Django
- APIs de core
- Autenticação JWT
- Endpoints públicos de pesquisa de satisfação (fora de /api/)
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from core.views import SatisfactionSurveyRateView, SatisfactionSurveyCommentView

urlpatterns = [
    # =========================================================
    # 1. ADMIN DO DJANGO
    # =========================================================
    path('admin/', admin.site.urls),
    
    # =========================================================
    # 2. AUTENTICAÇÃO JWT
    # =========================================================
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Login: obtém access + refresh token
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Renova access token
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),  # Verifica se token é válido
    
    # =========================================================
    # 3. APIs (REST)
    # =========================================================
    path('api/', include('core.urls')),
    
    # =========================================================
    # 4. PESQUISA DE SATISFAÇÃO (Público, fora de /api/)
    # =========================================================
    # Rating direto via botões no e-mail (1-5)
    path(
        'satisfaction-survey/<int:ticket_id>/rate/<int:rating>/',
        SatisfactionSurveyRateView.as_view(),
        name='satisfaction-survey-rate'
    ),
    # Adicionar comentário (opcional)
    path(
        'satisfaction-survey/<int:ticket_id>/comment/',
        SatisfactionSurveyCommentView.as_view(),
        name='satisfaction-survey-comment'
    ),
]