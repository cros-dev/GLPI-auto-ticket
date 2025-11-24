"""
URLs da API REST para o app core.

Define todas as rotas da API organizadas por funcionalidade:
1. Categorias GLPI
2. Webhook de tickets
3. API de tickets
4. Download de anexos
5. Configuração de GLPI ID
6. Classificação de tickets
"""
from django.urls import path
from .views import (
    GlpiCategoryListView,
    GlpiCategorySyncView,
    GlpiWebhookView,
    TicketListView,
    TicketDetailView,
    AttachmentDownloadView,
    SetGlpiIdView,
    TicketClassificationView
)

urlpatterns = [
    # =========================================================
    # 1. SINCRONIZAÇÃO E LISTA DE CATEGORIAS
    # =========================================================
    path('glpi/categories/', GlpiCategoryListView.as_view(), name='glpi-category-list'),
    path('glpi/categories/sync/', GlpiCategorySyncView.as_view(), name='glpi-category-sync'),

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
    # 4. DOWNLOAD DE ANEXOS
    # =========================================================
    path('attachments/<int:pk>/download/', AttachmentDownloadView.as_view(), name='attachment-download'),

    # =========================================================
    # 5. CONFIGURAÇÃO FINAL DO GLPI ID
    # =========================================================
    path('tickets/<int:pk>/set-glpi-id/', SetGlpiIdView.as_view(), name='ticket-set-glpi-id'),

    # =========================================================
    # 6. CLASSIFICAÇÃO DE TICKET
    # =========================================================
    path('tickets/classify/', TicketClassificationView.as_view(), name='ticket-classify'),
]