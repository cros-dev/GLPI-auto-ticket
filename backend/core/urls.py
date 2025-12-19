"""
URLs da API REST para o app core.

Define todas as rotas da API organizadas por funcionalidade:
1. Categorias GLPI
2. Webhook de tickets
3. API de tickets
4. Classificação de tickets
5. Sugestões de categorias (listagem, detalhe, edição, prévia, aprovação, rejeição)
"""
from django.urls import path
from .views import (
    GlpiCategoryListView,
    GlpiCategorySyncFromApiView,
    GlpiWebhookView,
    TicketListView,
    TicketDetailView,
    TicketClassificationView,
    CategorySuggestionListView,
    CategorySuggestionStatsView,
    CategorySuggestionUpdateView,
    CategorySuggestionApproveView,
    CategorySuggestionRejectView,
    CategorySuggestionPreviewView
)

urlpatterns = [
    # =========================================================
    # 1. SINCRONIZAÇÃO E LISTA DE CATEGORIAS
    # =========================================================
    path('glpi/categories/', GlpiCategoryListView.as_view(), name='glpi-category-list'),
    path('glpi/categories/sync-from-api/', GlpiCategorySyncFromApiView.as_view(), name='glpi-category-sync-from-api'),

    # =========================================================
    # 2. WEBHOOK DE TICKET (GLPI -> n8n -> Django)
    # =========================================================
    path('glpi/webhook/ticket/', GlpiWebhookView.as_view(), name='glpi-webhook-ticket'),

    # =========================================================
    # 3. API DE TICKETS (Para o Front-end)
    # =========================================================
    path('tickets/', TicketListView.as_view(), name='ticket-list'),
    path('tickets/<int:pk>/', TicketDetailView.as_view(), name='ticket-detail'),

    # =========================================================
    # 4. CLASSIFICAÇÃO DE TICKET
    # =========================================================
    path('tickets/classify/', TicketClassificationView.as_view(), name='ticket-classify'),

    # =========================================================
    # 5. SUGESTÕES DE CATEGORIAS
    # =========================================================
    path('category-suggestions/', CategorySuggestionListView.as_view(), name='category-suggestion-list'),
    path('category-suggestions/stats/', CategorySuggestionStatsView.as_view(), name='category-suggestion-stats'),
    path('category-suggestions/<int:pk>/', CategorySuggestionUpdateView.as_view(), name='category-suggestion-detail'),
    path('category-suggestions/preview/', CategorySuggestionPreviewView.as_view(), name='category-suggestion-preview'),
    path('category-suggestions/<int:pk>/approve/', CategorySuggestionApproveView.as_view(), name='category-suggestion-approve'),
    path('category-suggestions/<int:pk>/reject/', CategorySuggestionRejectView.as_view(), name='category-suggestion-reject'),

    # =========================================================
    # 6. PESQUISA DE SATISFAÇÃO
    # =========================================================
    # Endpoints públicos estão em config/urls.py
]