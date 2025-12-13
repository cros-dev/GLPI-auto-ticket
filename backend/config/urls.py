"""
URLs principais do projeto Django.

Define as rotas principais incluindo:
- Admin do Django
- APIs de accounts e core
- Endpoints públicos de pesquisa de satisfação (fora de /api/)
"""
from django.contrib import admin
from django.urls import path, include
from core.views import SatisfactionSurveyRateView, SatisfactionSurveyCommentView

urlpatterns = [
    # =========================================================
    # 1. ADMIN DO DJANGO
    # =========================================================
    path('admin/', admin.site.urls),
    
    # =========================================================
    # 2. APIs (REST)
    # =========================================================
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('core.urls')),
    
    # =========================================================
    # 3. PESQUISA DE SATISFAÇÃO (Público, fora de /api/)
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