"""
Serializers para validação e serialização de dados da API.

Este módulo contém todos os serializers usados para:
- Validação de dados de entrada
- Serialização de dados de saída
- Transformação entre modelos Django e JSON
"""
from rest_framework import serializers
from .models import Ticket, GlpiCategory, SatisfactionSurvey, CategorySuggestion
from .constants import VALID_ARTICLE_TYPES


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
# 2. TICKETS
# =========================================================

class TicketSerializer(serializers.ModelSerializer):
    """
    Serializer para tickets armazenados localmente.
    
    Representa o estado sincronizado do GLPI via n8n.
    Inclui todos os campos principais do ticket.
    """

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
            "last_glpi_update",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
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
    location = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField()
    content = serializers.CharField()
    category_id = serializers.IntegerField(required=False, allow_null=True)
    category_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    entity_id = serializers.IntegerField(required=False, allow_null=True)
    entity_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    team_assigned_id = serializers.IntegerField(required=False, allow_null=True)
    team_assigned_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)


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
    suggested_category_id = serializers.IntegerField(required=False, allow_null=True)
    confidence = serializers.CharField(help_text="Nível de confiança: high, medium, low")
    classification_method = serializers.CharField(help_text="Método usado: 'ai' (Google Gemini) ou 'keywords' (palavras-chave)")
    ticket_type = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="1 = incidente, 2 = requisição"
    )
    ticket_type_label = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Nome do tipo (incidente/requisição)"
    )


# =========================================================
# 6. PESQUISA DE SATISFAÇÃO
# =========================================================

class SatisfactionSurveySerializer(serializers.Serializer):
    """
    Serializer para receber dados da pesquisa de satisfação.
    
    Valida os dados recebidos quando o usuário responde à pesquisa
    de satisfação via botões no e-mail ou formulário de comentário.
    """
    ticket_id = serializers.IntegerField(
        help_text="ID do ticket relacionado à pesquisa"
    )
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        help_text="Nota de satisfação do usuário (1 a 5)"
    )
    comment = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Comentário opcional do usuário sobre o atendimento"
    )


# =========================================================
# 7. SUGESTÕES DE CATEGORIAS
# =========================================================

class CategorySuggestionReviewSerializer(serializers.Serializer):
    """
    Serializer para aprovação/rejeição de sugestões de categorias.
    
    Valida payload opcional enviado pelo frontend ao revisar uma sugestão.
    
    Campos:
        notes: Observações do revisor (opcional)
    """
    notes = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Notas opcionais sobre a aprovação/rejeição"
    )


class CategorySuggestionUpdateSerializer(serializers.Serializer):
    """
    Serializer para edição de sugestões de categorias.
    
    Permite editar o caminho sugerido e notas de sugestões pendentes.
    
    Campos:
        suggested_path: Caminho completo da categoria (obrigatório)
        notes: Notas adicionais sobre a sugestão (opcional)
    """
    suggested_path = serializers.CharField(
        max_length=1024,
        help_text="Caminho completo sugerido (ex.: 'TI > Requisição > Administrativo > Montagem de Setup > Transmissão/Vídeo Conferência')"
    )
    notes = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Notas adicionais sobre a sugestão"
    )


class CategorySuggestionListSerializer(serializers.ModelSerializer):
    """
    Serializer para listagem de sugestões de categorias.
    
    Usado para serializar sugestões de categorias na listagem.
    """
    ticket_id = serializers.IntegerField(source='ticket.id', read_only=True)
    ticket_title = serializers.CharField(read_only=True)
    ticket_content = serializers.CharField(read_only=True)
    
    class Meta:
        model = CategorySuggestion
        fields = [
            'id',
            'suggested_path',
            'ticket_id',
            'ticket_title',
            'ticket_content',
            'status',
            'created_at',
            'reviewed_at',
            'reviewed_by',
            'notes'
        ]


class KnowledgeBaseArticleRequestSerializer(serializers.Serializer):
    """
    Serializer para requisição de geração de artigo de Base de Conhecimento.
    
    Campos:
        article_type: Tipo do artigo ('conceitual', 'operacional' ou 'troubleshooting')
        category: Categoria da Base de Conhecimento
        context: Contexto do ambiente, sistemas, servidores, softwares envolvidos
    """
    article_type = serializers.ChoiceField(
        choices=VALID_ARTICLE_TYPES,
        help_text=f"Tipo do artigo: {', '.join(VALID_ARTICLE_TYPES)}"
    )
    category = serializers.CharField(
        max_length=512,
        help_text="Categoria da Base de Conhecimento (ex: 'RTV > AM > TI > Suporte > Técnicos > Jornal / Switcher > Playout')"
    )
    context = serializers.CharField(
        help_text="Contexto do ambiente, sistemas, servidores, softwares envolvidos"
    )


class KnowledgeBaseArticleItemSerializer(serializers.Serializer):
    """
    Serializer para um artigo individual de Base de Conhecimento.
    
    Campos:
        content: Texto completo do artigo
    """
    content = serializers.CharField(help_text="Texto completo do artigo")


class KnowledgeBaseArticleResponseSerializer(serializers.Serializer):
    """
    Serializer para resposta de geração de artigo de Base de Conhecimento.
    
    Campos:
        articles: Lista de artigos gerados (pode conter múltiplos artigos)
        article_type: Tipo do artigo gerado
        category: Categoria informada
    """
    articles = KnowledgeBaseArticleItemSerializer(many=True, help_text="Lista de artigos gerados")
    article_type = serializers.CharField(help_text="Tipo do artigo gerado")
    category = serializers.CharField(help_text="Categoria da Base de Conhecimento")