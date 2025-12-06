"""
Serializers para validação e serialização de dados da API.

Este módulo contém todos os serializers usados para:
- Validação de dados de entrada
- Serialização de dados de saída
- Transformação entre modelos Django e JSON
"""
from rest_framework import serializers
from .models import Ticket, Attachment, GlpiCategory


# =========================================================
# 1. CATEGORIAS GLPI
# =========================================================

class GlpiCategorySerializer(serializers.ModelSerializer):
    """
    Serializer para categorias GLPI armazenadas localmente.
    
    Usado para leitura de categorias com seus relacionamentos hierárquicos.
    Inclui o campo 'parent' para representar a hierarquia.
    """

    class Meta:
        model = GlpiCategory
        fields = ["id", "glpi_id", "name", "parent"]


# =========================================================
# 2. ANEXOS (METADADOS)
# =========================================================

class AttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer para anexos vinculados a um ticket.
    
    Retorna apenas metadados do anexo (nome, tipo MIME, tamanho).
    O arquivo binário em si é entregue pelo endpoint de download.
    """

    class Meta:
        model = Attachment
        fields = ["id", "name", "mime_type", "size", "created_at"]
        read_only_fields = ["id", "created_at"]


# =========================================================
# 3. TICKETS
# =========================================================

class TicketSerializer(serializers.ModelSerializer):
    """
    Serializer para tickets armazenados localmente.
    
    Representa o estado sincronizado do GLPI via n8n.
    Inclui os metadados dos anexos aninhados (attachments) e todos os
    campos principais do ticket.
    """
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "name",
            "content_html",
            "location",
            "category_name",
            "classification_method",
            "classification_confidence",
            "date_creation",
            "user_recipient_id",
            "user_recipient_name",
            "entity_id",
            "entity_name",
            "team_assigned_id",
            "team_assigned_name",
            "raw_payload",
            "attachments",
            "last_glpi_update",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "attachments",
            "last_glpi_update",
            "raw_payload",
            "classification_method",
            "classification_confidence",
        ]


# =========================================================
# 4. VALIDAÇÃO DO WEBHOOK (N8N → DJANGO)
# =========================================================

class GlpiWebhookSerializer(serializers.Serializer):
    """
    Valida o payload do n8n antes de criar/atualizar o ticket local.
    
    Valida todos os campos obrigatórios e opcionais recebidos do webhook
    do GLPI via n8n na GlpiWebhookView.
    """
    id = serializers.IntegerField()
    date_creation = serializers.DateTimeField()
    user_recipient_id = serializers.IntegerField()
    user_recipient_name = serializers.CharField()
    location = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField()
    content = serializers.CharField()
    category_id = serializers.IntegerField(required=False, allow_null=True)
    category_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    entity_id = serializers.IntegerField(required=False, allow_null=True)
    entity_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    team_assigned_id = serializers.IntegerField(required=False, allow_null=True)
    team_assigned_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# =========================================================
# 5. CLASSIFICAÇÃO DE TICKET
# =========================================================

class TicketClassificationSerializer(serializers.Serializer):
    """
    Serializer para receber dados do ticket para classificação.
    
    Valida os dados de entrada necessários para classificar um ticket
    e sugerir uma categoria GLPI apropriada.
    
    O glpi_ticket_id é obrigatório para atualizar automaticamente o ticket
    com a categoria sugerida após a classificação.
    """
    title = serializers.CharField(help_text="Título do ticket")
    content = serializers.CharField(help_text="Conteúdo/descrição do ticket")
    glpi_ticket_id = serializers.IntegerField(
        required=True,
        help_text="ID do ticket no GLPI (obrigatório). Atualiza o ticket com a categoria sugerida. O ID do Django é o mesmo do GLPI."
    )


class TicketClassificationResponseSerializer(serializers.Serializer):
    """
    Serializer para resposta da classificação de ticket.
    
    Retorna a categoria sugerida com nível de confiança e informações
    adicionais sobre o resultado da classificação.
    """
    suggested_category_name = serializers.CharField()
    suggested_category_id = serializers.IntegerField(allow_null=True)
    confidence = serializers.CharField(help_text="Nível de confiança: high, medium, low")
    classification_method = serializers.CharField(help_text="Método usado: 'ai' (Google Gemini) ou 'keywords' (palavras-chave)")
    ticket_type = serializers.IntegerField(
        allow_null=True,
        required=False,
        help_text="1 = incidente, 2 = requisição"
    )
    ticket_type_label = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="Nome do tipo (incidente/requisição)"
    )