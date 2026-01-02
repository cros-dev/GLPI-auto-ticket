"""
Views da API REST para gerenciamento de tickets e categorias GLPI.

Este módulo contém todas as views que expõem endpoints da API:
- Categorias: listagem e sincronização
- Tickets: webhook, listagem, detalhe e classificação
- Sugestões de categorias: listagem, prévia, aprovação e rejeição
- Pesquisa de satisfação: endpoints públicos para avaliação
"""
from typing import Optional, Tuple
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import render
import logging

from .models import GlpiCategory, Ticket, CategorySuggestion, SatisfactionSurvey, KnowledgeBaseArticle
from .serializers import (
    GlpiCategorySerializer, 
    TicketSerializer, 
    GlpiWebhookSerializer,
    TicketClassificationSerializer,
    TicketClassificationResponseSerializer,
    SatisfactionSurveySerializer,
    CategorySuggestionReviewSerializer,
    CategorySuggestionUpdateSerializer,
    CategorySuggestionListSerializer,
    KnowledgeBaseArticleRequestSerializer,
    KnowledgeBaseArticleResponseSerializer
)
from .services import (
    classify_ticket,
    classify_ticket_with_gemini,
    generate_category_suggestion,
    save_preview_suggestion,
    determine_ticket_type,
    generate_knowledge_base_article,
    save_knowledge_base_articles,
    update_ticket_with_classification,
    handle_classification_failure,
    process_suggestion_review,
    parse_suggestion_path,
    find_category_by_path,
    process_categories_sync,
    process_webhook_ticket,
    process_survey_rating,
    process_survey_comment
)
from .clients.glpi_client import GlpiLegacyClient

logger = logging.getLogger(__name__)


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================





def _get_suggestion_or_404(pk: int) -> Tuple[Optional[CategorySuggestion], Optional[Response]]:
    """
    Busca uma sugestão de categoria ou retorna erro 404.
    
    Args:
        pk: ID da sugestão
        
    Returns:
        Tuple[Optional[CategorySuggestion], Optional[Response]]: 
            (suggestion, error_response)
            - suggestion: Instância de CategorySuggestion ou None
            - error_response: Response com erro 404 ou None
    """
    try:
        suggestion = CategorySuggestion.objects.get(pk=pk)
        return suggestion, None
    except CategorySuggestion.DoesNotExist:
        return None, Response(
            {"detail": "Sugestão não encontrada"},
            status=status.HTTP_404_NOT_FOUND
        )


def _validate_and_get_suggestion(pk: int) -> Tuple[Optional[CategorySuggestion], Optional[Response]]:
    """
    Valida e retorna uma sugestão de categoria pendente.
    
    Args:
        pk: ID da sugestão
        
    Returns:
        Tuple[Optional[CategorySuggestion], Optional[Response]]:
            (suggestion, error_response)
            - suggestion: Instância de CategorySuggestion ou None
            - error_response: Response com erro ou None
    """
    suggestion, error_response = _get_suggestion_or_404(pk)
    if error_response:
        return None, error_response
    
    if suggestion.status != 'pending':
        return None, Response(
            {"detail": f"Sugestão já foi {suggestion.get_status_display().lower()}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return suggestion, None




def _validate_survey_ticket(ticket_id_str):
    """
    Valida e retorna um ticket para pesquisa de satisfação.
    
    Args:
        ticket_id_str: ID do ticket como string
        
    Returns:
        tuple: (ticket, error_context)
               ticket: Instância de Ticket ou None
               error_context: Dict com erro para render ou None
    """
    try:
        ticket_id = int(ticket_id_str)
    except (ValueError, TypeError):
        return None, {'error': 'ID do ticket inválido.'}
    
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        return ticket, None
    except Ticket.DoesNotExist:
        return None, {'error': f'Ticket #{ticket_id} não encontrado.'}








# =========================================================
# 1. LISTA E SINCRONIZAÇÃO DE CATEGORIAS
# =========================================================

class GlpiCategoryListView(generics.ListAPIView):
    """
    Lista todas as categorias GLPI armazenadas localmente.
    
    Endpoint: GET /api/glpi/categories/
    Retorna todas as categorias com seus relacionamentos hierárquicos.
    """
    queryset = GlpiCategory.objects.all()
    serializer_class = GlpiCategorySerializer


class GlpiCategorySyncFromApiView(APIView):
    """
    Sincroniza categorias GLPI diretamente da API Legacy do GLPI.
    
    Endpoint: POST /api/glpi/categories/sync-from-api/
    
    Busca todas as categorias ITIL do GLPI via API Legacy e sincroniza
    com o banco de dados local. Este é o método recomendado para manter
    as categorias atualizadas automaticamente.
    
    Requer autenticação por token.
    
    O endpoint executa upsert usando o glpi_id informado, garantindo que o
    relacionamento pai/filho seja recriado no Django exatamente como no GLPI.
    
    IMPORTANTE: O Django funciona como espelho do GLPI. Categorias que não estão
    na API serão removidas automaticamente do banco de dados.
    
    Configuração necessária no .env:
        GLPI_LEGACY_API_URL=http://172.16.0.180:81/apirest.php
        GLPI_LEGACY_API_USER=glpi
        GLPI_LEGACY_API_PASSWORD=senha
        GLPI_LEGACY_APP_TOKEN=token_app (opcional)
    
    Nota: A URL deve ser configurada completa, incluindo o caminho da API.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            glpi_client = GlpiLegacyClient()
            categories = glpi_client.fetch_categories()
            
            if not categories:
                return Response(
                    {"detail": "Nenhuma categoria encontrada na API do GLPI."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = process_categories_sync(categories, source_name="API")
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro ao buscar categorias da API GLPI: {str(e)}")
            return Response(
                {"detail": f"Erro ao conectar com a API do GLPI: {str(e)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


# =========================================================
# 2. RECEBE TICKET DO N8N, TRATA E SALVA NO BANCO (WEBHOOK)
# =========================================================

class GlpiWebhookView(APIView):
    """
    Recebe um ticket vindo do GLPI via n8n.
    
    Endpoint: POST /api/glpi/webhook/ticket/
    Fluxo: GLPI → n8n → Django
    
    Requer autenticação JWT no header:
    Authorization: Bearer <access_token_aqui>
    
    Valida o payload, limpa o HTML do conteúdo e salva/atualiza o ticket
    no banco de dados local.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = GlpiWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ticket = process_webhook_ticket(data, request.data)

        return Response(
            {"detail": "Ticket atualizado", "ticket": TicketSerializer(ticket).data},
            status=status.HTTP_200_OK
        )


# =========================================================
# 3. LISTA E DETALHE DE TICKETS (Para o Front-end/API)
# =========================================================

class TicketListView(generics.ListAPIView):
    """
    Lista todos os tickets armazenados localmente.
    
    Endpoint: GET /api/tickets/
    Requer autenticação por token.
    Retorna tickets ordenados por data de criação (mais recentes primeiro).
    """
    queryset = Ticket.objects.all().order_by("-created_at")
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]


class TicketDetailView(generics.RetrieveUpdateAPIView):
    """
    Detalha ou atualiza um ticket local.
    
    Endpoint: GET/PUT/PATCH /api/tickets/<id>/
    Requer autenticação por token.
    Permite visualizar e atualizar um ticket específico.
    """
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]


# =========================================================
# 4. CLASSIFICAÇÃO DE TICKET
# =========================================================

class TicketClassificationView(APIView):
    """
    Classifica um ticket e sugere categoria usando Google Gemini AI (quando disponível).
    
    Endpoint: POST /api/tickets/classify/
    Requer autenticação por token.
    
    Recebe título e conteúdo do ticket e retorna categoria sugerida baseada
    nas categorias GLPI salvas localmente. Tenta usar Gemini AI primeiro, 
    se não estiver configurado ou falhar, usa classificação por palavras-chave.
    
    Se glpi_ticket_id for fornecido, atualiza automaticamente o ticket
    com a categoria sugerida. O ID do ticket no Django é o mesmo do GLPI.
    
    Payload esperado:
        {
            "title": "Título",
            "content": "Conteúdo",
            "glpi_ticket_id": 86  // obrigatório: ID do ticket (mesmo do GLPI)
        }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = TicketClassificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        glpi_ticket_id = data.get("glpi_ticket_id")
        result = classify_ticket(
            title=data["title"],
            content=data.get("content", ""),
            ticket_id=glpi_ticket_id
        )
        
        if isinstance(result, dict) and 'error' in result:
            error_type = result.get('error', 'unknown')
            error_message = result.get('message', 'Erro ao classificar ticket com Gemini AI.')
            
            # Erros temporários retornam 503, erros de configuração retornam 400
            if error_type in ('service_unavailable', 'quota_exceeded'):
                return Response(
                    {"detail": error_message},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            return Response(
                {"detail": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if result:
            if glpi_ticket_id:
                update_ticket_with_classification(glpi_ticket_id, result)
            
            response_serializer = TicketClassificationResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            suggestion_created = False
            
            if glpi_ticket_id:
                _, suggestion_created = handle_classification_failure(glpi_ticket_id)
            
            detail_message = "Não foi possível classificar o ticket. Verifique se há categorias cadastradas."
            if suggestion_created:
                detail_message += " Uma sugestão de categoria foi criada automaticamente e está aguardando revisão. Acesse /api/category-suggestions/ para visualizar."
            
            return Response(
                {"detail": detail_message},
                status=status.HTTP_400_BAD_REQUEST
            )


# =========================================================
# 7. SUGESTÕES DE CATEGORIAS
# =========================================================

class CategorySuggestionListView(generics.ListAPIView):
    """
    Lista sugestões de categorias geradas pela IA.
    
    Endpoint: GET /api/category-suggestions/?status=pending
    Requer autenticação por token.
    
    Parâmetros de query:
        - status: Filtra por status (pending, approved, rejected). 
                  Se não informado, retorna apenas pendentes.
    
    Retorna sugestões para revisão manual.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = CategorySuggestion.objects.all().order_by('-created_at')
        status_filter = self.request.query_params.get('status', None)
        source_filter = self.request.query_params.get('source', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            queryset = queryset.filter(status='pending')
        
        # Filtro opcional por origem (ticket ou preview)
        if source_filter:
            queryset = queryset.filter(source=source_filter)
        
        return queryset
    
    serializer_class = CategorySuggestionListSerializer


class CategorySuggestionStatsView(APIView):
    """
    Retorna estatísticas agregadas das sugestões de categorias.
    
    Endpoint: GET /api/category-suggestions/stats/
    Requer autenticação por token.
    
    Retorna contagem de sugestões por status (total, pending, approved, rejected).
    Útil para exibir dashboard com estatísticas resumidas.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        stats = {
            'total': CategorySuggestion.objects.count(),
            'pending': CategorySuggestion.objects.filter(status='pending').count(),
            'approved': CategorySuggestion.objects.filter(status='approved').count(),
            'rejected': CategorySuggestion.objects.filter(status='rejected').count()
        }
        return Response(stats, status=status.HTTP_200_OK)


class CategorySuggestionApproveView(APIView):
    """
    Aprova uma sugestão de categoria.
    
    Endpoint: POST /api/category-suggestions/<id>/approve/
    Requer autenticação por token.
    
    Fluxo:
    - Notifica o n8n para criar/atualizar a categoria no GLPI
    - Confirma a aprovação (status=approved) e salva no banco
    
    Payload opcional:
        {
            "notes": "Notas sobre a aprovação"
        }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        suggestion, error_response = _validate_and_get_suggestion(pk)
        if error_response:
            return error_response
        
        serializer = CategorySuggestionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reviewed_at = timezone.now()
        reviewed_by = request.user.username if request.user.is_authenticated else 'api'
        notes = (serializer.validated_data.get('notes') or '').strip()
        
        success, error_message = process_suggestion_review(
            suggestion=suggestion,
            new_status='approved',
            notes=notes,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at
        )
        
        if not success:
            return Response(
                {"detail": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {
                "detail": "Sugestão aprovada",
                "suggestion": {
                    "id": suggestion.id,
                    "suggested_path": suggestion.suggested_path,
                    "status": suggestion.status
                }
            },
            status=status.HTTP_200_OK
        )


class CategorySuggestionRejectView(APIView):
    """
    Rejeita uma sugestão de categoria.
    
    Endpoint: POST /api/category-suggestions/<id>/reject/
    Requer autenticação por token.
    
    Fluxo:
    - Notifica o n8n para aplicar a rejeição conforme o fluxo do projeto
    - Confirma a rejeição (status=rejected) e salva no banco
    
    Payload opcional:
        {
            "notes": "Motivo da rejeição"
        }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        suggestion, error_response = _validate_and_get_suggestion(pk)
        if error_response:
            return error_response
        
        serializer = CategorySuggestionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reviewed_at = timezone.now()
        reviewed_by = request.user.username if request.user.is_authenticated else 'api'
        notes = (serializer.validated_data.get('notes') or '').strip()
        
        success, error_message = process_suggestion_review(
            suggestion=suggestion,
            new_status='rejected',
            notes=notes,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at
        )
        
        if not success:
            return Response(
                {"detail": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {
                "detail": "Sugestão rejeitada",
                "suggestion": {
                    "id": suggestion.id,
                    "suggested_path": suggestion.suggested_path,
                    "status": suggestion.status
                }
            },
            status=status.HTTP_200_OK
        )


class CategorySuggestionUpdateView(APIView):
    """
    Edita uma sugestão de categoria pendente.
    
    Endpoint: GET /api/category-suggestions/<id>/ - Retorna detalhes da sugestão
    Endpoint: PUT /api/category-suggestions/<id>/ - Atualiza sugestão completa
    Endpoint: PATCH /api/category-suggestions/<id>/ - Atualiza sugestão parcialmente
    Requer autenticação por token.
    
    Permite editar apenas sugestões com status 'pending'.
    Campos editáveis: suggested_path e notes.
    
    Payload esperado:
        {
            "suggested_path": "TI > Requisição > Acesso > GLPI > Criação de Usuário / Conta",
            "notes": "Notas opcionais"
        }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Retorna detalhes da sugestão."""
        suggestion, error_response = _get_suggestion_or_404(pk)
        if error_response:
            return error_response
        
        return Response({
            'id': suggestion.id,
            'suggested_path': suggestion.suggested_path,
            'ticket_id': suggestion.ticket.id if suggestion.ticket else None,
            'ticket_title': suggestion.ticket_title,
            'ticket_content': suggestion.ticket_content if suggestion.ticket_content else '',
            'status': suggestion.status,
            'source': suggestion.source,
            'notes': suggestion.notes,
            'created_at': suggestion.created_at,
            'updated_at': suggestion.updated_at,
            'reviewed_at': suggestion.reviewed_at,
            'reviewed_by': suggestion.reviewed_by
        }, status=status.HTTP_200_OK)
    
    def put(self, request, pk):
        """Atualiza sugestão completa."""
        return self._update_suggestion(request, pk)
    
    def patch(self, request, pk):
        """Atualiza sugestão parcialmente."""
        return self._update_suggestion(request, pk)
    
    def _update_suggestion(self, request, pk):
        """Método auxiliar para atualizar sugestão."""
        suggestion, error_response = _get_suggestion_or_404(pk)
        if error_response:
            return error_response
        
        if suggestion.status != 'pending':
            return Response(
                {"detail": f"Não é possível editar sugestão com status '{suggestion.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CategorySuggestionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        suggested_path = serializer.validated_data.get('suggested_path', '').strip()
        notes = serializer.validated_data.get('notes', '').strip()
        
        suggestion.suggested_path = suggested_path
        suggestion.notes = notes
        suggestion.save()
        
        return Response({
            "detail": "Sugestão atualizada com sucesso",
            "suggestion": {
                "id": suggestion.id,
                "suggested_path": suggestion.suggested_path,
                "notes": suggestion.notes,
                "status": suggestion.status
            }
        }, status=status.HTTP_200_OK)


class CategorySuggestionPreviewView(APIView):
    """
    Gera uma prévia de sugestão de categoria sem salvar.
    
    Endpoint: POST /api/category-suggestions/preview/
    Requer autenticação por token.
    
    Útil para testar e validar sugestões antes de criar categorias no GLPI.
    Primeiro tenta encontrar uma categoria existente no banco. Se não encontrar,
    gera uma nova sugestão hierárquica usando IA.
    
    Recebe título e conteúdo e retorna a categoria encontrada ou sugestão gerada.
    
    Payload esperado:
    {
        "title": "Título do ticket",
        "content": "Conteúdo/descrição do ticket"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Usa serializer para validação ao invés de validação manual
        serializer = TicketClassificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        
        result = classify_ticket_with_gemini(title, content)
        
        if result and isinstance(result, dict) and 'error' in result:
            return Response(
                {"detail": result.get('message', 'Erro ao classificar ticket com Gemini AI.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if result and isinstance(result, dict) and 'suggested_category_name' in result:
            return Response(
                {
                    "suggested_path": result.get('suggested_category_name', ''),
                    "suggested_category_id": result.get('suggested_category_id'),
                    "ticket_type": result.get('ticket_type'),
                    "ticket_type_label": result.get('ticket_type_label'),
                    "classification_method": "existing_category",
                    "confidence": result.get('confidence', 'high'),
                    "note": "Categoria existente encontrada. Esta é apenas uma prévia."
                },
                status=status.HTTP_200_OK
            )
        
        suggested_path = generate_category_suggestion(title, content)
        
        if isinstance(suggested_path, dict) and 'error' in suggested_path:
            return Response(
                {"detail": suggested_path.get('message', 'Erro ao gerar sugestão de categoria com Gemini AI.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not suggested_path:
            return Response(
                {"detail": "Não foi possível gerar uma sugestão de categoria para o contexto fornecido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        category_name, parent_path, error_message = parse_suggestion_path(suggested_path)
        if error_message:
            return Response(
                {"detail": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if parent_path:
            path_parts = [part.strip() for part in parent_path.split('>') if part.strip()]
            path_parts.append(category_name)
        else:
            path_parts = [category_name]
        ticket_type, ticket_type_label = determine_ticket_type(path_parts)
        
        saved_suggestion = save_preview_suggestion(suggested_path, title, content)
        suggestion_id = saved_suggestion.id if saved_suggestion else None
        
        return Response(
            {
                "suggested_path": suggested_path,
                "ticket_type": ticket_type,
                "ticket_type_label": ticket_type_label,
                "classification_method": "new_suggestion",
                "suggestion_id": suggestion_id,
                "note": "Nova sugestão gerada (categoria não encontrada). Esta prévia foi salva para revisão."
            },
            status=status.HTTP_200_OK
        )


# =========================================================
# 8. PESQUISA DE SATISFAÇÃO
# =========================================================

class SatisfactionSurveyRateView(APIView):
    """
    Recebe avaliação direta via GET e salva imediatamente.
    
    Endpoint: GET /satisfaction-survey/<ticket_id>/rate/<rating>/?token=<token>
    
    Usado por botões no e-mail do GLPI que enviam rating diretamente.
    Gera token na primeira requisição e valida nas subsequentes.
    Retorna página de sucesso ou redireciona para página de comentário.
    """
    permission_classes = []
    
    def get(self, request, ticket_id, rating):
        """Processa avaliação direta e salva."""
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            return render(request, 'satisfaction_survey/success.html', {
                'error': 'Rating inválido.',
                'rating': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if rating < 1 or rating > 5:
            return render(request, 'satisfaction_survey/success.html', {
                'error': 'Rating deve ser entre 1 e 5.',
                'rating': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        ticket, error_context = _validate_survey_ticket(ticket_id)
        if error_context:
            return render(request, 'satisfaction_survey/success.html', {
                **error_context,
                'rating': None
            }, status=status.HTTP_404_NOT_FOUND if 'não encontrado' in error_context.get('error', '') else status.HTTP_400_BAD_REQUEST)
        
        provided_token = request.GET.get('token', '').strip()
        comment = request.GET.get('comment', '').strip()
        
        survey, error_message = process_survey_rating(
            ticket=ticket,
            rating=rating,
            provided_token=provided_token,
            comment=comment
        )
        
        if error_message:
            return render(request, 'satisfaction_survey/success.html', {
                'error': error_message,
                'rating': None
            }, status=status.HTTP_403_FORBIDDEN)
        
        return render(request, 'satisfaction_survey/success.html', {
            'rating': rating,
            'ticket_id': ticket_id,
            'ticket': ticket,
            'has_comment': bool(survey.comment),
            'comment': survey.comment,
            'token': survey.token
        })
    
class SatisfactionSurveyCommentView(APIView):
    """
    Página para adicionar/editar comentário na pesquisa de satisfação.
    
    Endpoint: GET /satisfaction-survey/<ticket_id>/comment/ - Exibe formulário
    Endpoint: POST /satisfaction-survey/<ticket_id>/comment/ - Salva comentário
    """
    permission_classes = []
    
    def get(self, request, ticket_id):
        """Renderiza formulário para adicionar comentário."""
        ticket, error_context = _validate_survey_ticket(ticket_id)
        if error_context:
            return render(request, 'satisfaction_survey/comment.html', error_context,
                        status=status.HTTP_404_NOT_FOUND if 'não encontrado' in error_context.get('error', '') else status.HTTP_400_BAD_REQUEST)
        
        survey = SatisfactionSurvey.objects.filter(ticket=ticket).first()
        provided_token = request.GET.get('token', '').strip()
        
        from .services import _validate_survey_token
        if not _validate_survey_token(survey, provided_token):
            return render(request, 'satisfaction_survey/comment.html', {
                'error': 'Token inválido ou expirado. Esta pesquisa já foi respondida.',
                'ticket': ticket
            }, status=status.HTTP_403_FORBIDDEN)
        
        context = {
            'ticket': ticket,
            'survey': survey,
            'has_rating': survey is not None,
            'token': survey.token if survey else None
        }
        
        return render(request, 'satisfaction_survey/comment.html', context)
    
    def post(self, request, ticket_id):
        """Salva comentário na pesquisa."""
        ticket, error_context = _validate_survey_ticket(ticket_id)
        if error_context:
            return render(request, 'satisfaction_survey/comment.html', error_context,
                        status=status.HTTP_404_NOT_FOUND if 'não encontrado' in error_context.get('error', '') else status.HTTP_400_BAD_REQUEST)
        
        comment = request.POST.get('comment', '').strip()
        provided_token = request.POST.get('token', request.GET.get('token', '')).strip()
        
        survey, error_message = process_survey_comment(
            ticket=ticket,
            comment=comment,
            provided_token=provided_token
        )
        
        if error_message:
            return render(request, 'satisfaction_survey/comment.html', {
                'error': error_message,
                'ticket': ticket,
                'survey': SatisfactionSurvey.objects.filter(ticket=ticket).first()
            }, status=status.HTTP_403_FORBIDDEN)
        
        return render(request, 'satisfaction_survey/success.html', {
            'rating': survey.rating,
            'ticket_id': ticket_id,
            'ticket': ticket,
            'has_comment': True,
            'comment': comment,
            'token': survey.token
        })


class KnowledgeBaseArticleView(APIView):
    """
    View para geração de artigos de Base de Conhecimento usando IA.
    
    Endpoint: POST /api/knowledge-base/article/
    
    Requer autenticação.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Gera um artigo de Base de Conhecimento baseado nos parâmetros fornecidos.
        
        Body esperado:
        {
            "article_type": "conceitual" | "operacional" | "troubleshooting",
            "category": "RTV > AM > TI > Suporte > Técnicos > Jornal / Switcher > Playout",
            "context": "Descrição do ambiente, sistemas, servidores..."
        }
        
        Retorna:
        {
            "articles": [
                {"content": "Texto completo do artigo 1"},
                {"content": "Texto completo do artigo 2"}
            ],
            "article_type": "conceitual",
            "category": "RTV > AM > TI > Suporte > Técnicos > Jornal / Switcher > Playout"
        }
        """
        serializer = KnowledgeBaseArticleRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Dados inválidos', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        article_type = serializer.validated_data['article_type']
        category = serializer.validated_data['category']
        context = serializer.validated_data['context']
        
        logger.info(f"Geração de artigo de Base de Conhecimento solicitada. Tipo: {article_type}, Categoria: {category}")
        
        result = generate_knowledge_base_article(
            article_type=article_type,
            category=category,
            context=context
        )
        
        if result is None:
            return Response(
                {'error': 'Geração não disponível', 'message': 'A API do Gemini não está configurada ou não está disponível'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        if isinstance(result, dict) and 'error' in result:
            error_message = result.get('message', 'Erro desconhecido ao gerar artigo')
            error_type = result.get('error', 'unknown_error')
            
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            if error_type in ['invalid_article_type', 'missing_category', 'missing_context']:
                status_code = status.HTTP_400_BAD_REQUEST
            elif error_type == 'library_not_installed':
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            
            return Response(
                {'error': error_type, 'message': error_message},
                status=status_code
            )
        
        if 'articles' in result and result['articles']:
            saved_articles = save_knowledge_base_articles(
                article_type=article_type,
                category=category,
                context=context,
                articles=result['articles']
            )
            if saved_articles:
                for i, article in enumerate(result['articles']):
                    if i < len(saved_articles):
                        article['id'] = saved_articles[i].id
        
        response_serializer = KnowledgeBaseArticleResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)