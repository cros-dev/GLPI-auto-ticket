"""
Views da API REST para gerenciamento de tickets e categorias GLPI.

Este módulo contém todas as views que expõem endpoints da API:
- Categorias: listagem e sincronização
- Tickets: webhook, listagem, detalhe e classificação
- Sugestões de categorias: listagem, prévia, aprovação e rejeição
- Pesquisa de satisfação: endpoints públicos para avaliação
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from django.utils import timezone
from django.shortcuts import render
from django.conf import settings
import requests
import logging

from .models import GlpiCategory, Ticket, CategorySuggestion, SatisfactionSurvey
from .serializers import (
    GlpiCategorySerializer, 
    TicketSerializer, 
    GlpiWebhookSerializer,
    TicketClassificationSerializer,
    TicketClassificationResponseSerializer,
    SatisfactionSurveySerializer
)
from .utils import clean_html_content
from .services import (
    classify_ticket,
    classify_ticket_with_gemini,
    generate_category_suggestion,
    determine_ticket_type
)

logger = logging.getLogger(__name__)


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def _find_category_by_path(path):
    """
    Busca uma categoria existente no banco percorrendo o caminho informado.
    
    Args:
        path: Caminho hierárquico (ex.: "TI > Requisição")
        
    Returns:
        GlpiCategory ou None: Categoria encontrada ou None se não existir
    """
    if not path:
        return None
    
    parts = [p.strip() for p in path.split('>') if p.strip()]
    parent = None
    for part in parts:
        parent = GlpiCategory.objects.filter(name=part, parent=parent).first()
        if not parent:
            return None
    return parent


def _process_categories_sync(categories, source_name="fonte"):
    """
    Processa lista de categorias e cria/atualiza no banco.
    Remove categorias que não estão na fonte para manter o Django como espelho do GLPI.
    
    Args:
        categories: Lista de dicionários contendo:
            - glpi_id: ID da categoria no GLPI
            - full_path: Caminho completo (ex.: "TI > Requisição > Acesso")
            - parts: Lista de partes do caminho
            - parent_path: Caminho do pai (ex.: "TI > Requisição")
        source_name: Nome da fonte (para logs/mensagens de erro)
        
    Returns:
        dict: Estatísticas de criação/atualização/remoção
    """
    created_count = 0
    updated_count = 0
    cache_by_path = {}
    
    source_glpi_ids = {entry["glpi_id"] for entry in categories}
    
    sorted_categories = sorted(categories, key=lambda item: len(item["parts"]))
    
    for entry in sorted_categories:
        category_name = entry["parts"][-1]
        parent_path = entry["parent_path"]
        parent = None
        
        if parent_path:
            parent = cache_by_path.get(parent_path)
            if not parent:
                parent = _find_category_by_path(parent_path)
            if not parent:
                parent_segments = [p.strip() for p in parent_path.split('>') if p.strip()]
                if len(parent_segments) > 1:
                    logger.warning(f"Categoria pai '{parent_path}' não encontrada na {source_name}. Criando sem pai.")
        
        obj, created = GlpiCategory.objects.update_or_create(
            glpi_id=entry["glpi_id"],
            defaults={
                "name": category_name,
                "parent": parent,
                "full_path": entry["full_path"]
            }
        )
        
        cache_by_path[entry["full_path"]] = obj
        if created:
            created_count += 1
        else:
            updated_count += 1
    
    deleted_count = 0
    if source_glpi_ids:
        categories_to_delete = GlpiCategory.objects.exclude(glpi_id__in=source_glpi_ids)
        deleted_count = categories_to_delete.count()
        categories_to_delete.delete()

    return {
        "created": created_count,
        "updated": updated_count,
        "deleted": deleted_count,
        "total": GlpiCategory.objects.count()
    }


def _notify_n8n_survey(ticket_id, rating, comment):
    """
    Notifica n8n para atualizar pesquisa de satisfação no GLPI.
    
    Args:
        ticket_id: ID do ticket
        rating: Nota de satisfação (1-5)
        comment: Comentário opcional
    """
    n8n_webhook_url = getattr(settings, 'N8N_WEBHOOK_URL', None)
    
    if not n8n_webhook_url:
        return
    
    try:
        payload = {
            'ticket_id': ticket_id,
            'rating': rating,
            'comment': comment or '',
            'type': 'satisfaction-survey-update'
        }
        
        response = requests.post(
            n8n_webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Erro ao notificar n8n: {str(e)}")


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
        GLPI_LEGACY_API_URL=http://172.16.0.180:81
        GLPI_LEGACY_API_USER=glpi
        GLPI_LEGACY_API_PASSWORD=senha
        GLPI_LEGACY_APP_TOKEN=token_app (opcional)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            categories = self._fetch_categories_from_api()
            if not categories:
                return Response(
                    {"detail": "Nenhuma categoria encontrada na API do GLPI."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            result = _process_categories_sync(categories, source_name="API")
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except requests.RequestException as e:
            logger.error(f"Erro ao buscar categorias da API GLPI: {str(e)}")
            return Response(
                {"detail": f"Erro ao conectar com a API do GLPI: {str(e)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    
    def _get_session_token(self):
        """
        Obtém token de sessão da API Legacy do GLPI.
        
        Returns:
            str: Session token para autenticação
            
        Raises:
            requests.RequestException: Se houver erro na autenticação
        """
        glpi_url = getattr(settings, 'GLPI_LEGACY_API_URL', None)
        glpi_user = getattr(settings, 'GLPI_LEGACY_API_USER', None)
        glpi_password = getattr(settings, 'GLPI_LEGACY_API_PASSWORD', None)
        glpi_app_token = getattr(settings, 'GLPI_LEGACY_APP_TOKEN', None)
        
        if not glpi_url or not glpi_user or not glpi_password:
            raise ValueError("Configuração da API Legacy do GLPI incompleta. Verifique GLPI_LEGACY_API_URL, GLPI_LEGACY_API_USER e GLPI_LEGACY_API_PASSWORD no .env")
        
        glpi_url = glpi_url.rstrip('/')
        if glpi_url.endswith('/apirest.php'):
            base_url = glpi_url
        else:
            base_url = f"{glpi_url}/apirest.php"
        
        headers = {
            'Content-Type': 'application/json'
        }
        if glpi_app_token:
            headers['App-Token'] = glpi_app_token
        
        response = requests.post(
            f"{base_url}/initSession",
            json={
                "login": glpi_user,
                "password": glpi_password
            },
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if 'session_token' not in data:
            raise ValueError("Token de sessão não retornado pela API do GLPI")
        
        return data['session_token']
    
    def _fetch_categories_from_api(self):
        """
        Busca todas as categorias ITIL da API Legacy do GLPI.
        
        Returns:
            list: Lista de dicionários contendo caminho completo, partes e glpi_id
            
        Raises:
            requests.RequestException: Se houver erro na requisição
            ValueError: Se houver erro ao processar os dados
        """
        glpi_url = getattr(settings, 'GLPI_LEGACY_API_URL', None)
        if not glpi_url:
            raise ValueError("GLPI_LEGACY_API_URL não configurado")
        
        glpi_url = glpi_url.rstrip('/')
        if glpi_url.endswith('/apirest.php'):
            base_url = glpi_url
        else:
            base_url = f"{glpi_url}/apirest.php"
        
        session_token = self._get_session_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Session-Token': session_token
        }
        glpi_app_token = getattr(settings, 'GLPI_LEGACY_APP_TOKEN', None)
        if glpi_app_token:
            headers['App-Token'] = glpi_app_token
        
        all_categories = []
        range_start = 0
        range_limit = 50
        
        while True:
            response = requests.get(
                f"{base_url}/ITILCategory/?expand_dropdowns=true&range={range_start}-{range_start + range_limit - 1}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            categories_batch = response.json()
            if not categories_batch or not isinstance(categories_batch, list):
                break
            
            all_categories.extend(categories_batch)
            
            content_range = response.headers.get('Content-Range', '')
            if content_range:
                range_info = content_range.split('/')
                if len(range_info) == 2:
                    current_range = range_info[0]
                    total_count = int(range_info[1])
                    if '-' in current_range:
                        current_end = int(current_range.split('-')[1])
                        if current_end >= total_count - 1:
                            break
            
            range_start += range_limit
            
            if len(categories_batch) < range_limit:
                break
        
        processed_categories = []
        seen_ids = set()
        
        for category in all_categories:
            glpi_id = category.get('id')
            if not glpi_id or glpi_id in seen_ids:
                continue
            
            seen_ids.add(glpi_id)
            completename = category.get('completename', '')
            
            if not completename:
                name = category.get('name', '')
                if name:
                    completename = name
            
            if not completename:
                continue
            
            parts = [p.strip() for p in completename.split('>') if p.strip()]
            if not parts:
                continue
            
            processed_categories.append({
                "full_path": ' > '.join(parts),
                "parts": parts,
                "parent_path": ' > '.join(parts[:-1]) if len(parts) > 1 else '',
                "glpi_id": glpi_id,
            })
        
        return processed_categories
    

# =========================================================
# 2. RECEBE TICKET DO N8N, TRATA E SALVA NO BANCO (WEBHOOK)
# =========================================================

class GlpiWebhookView(APIView):
    """
    Recebe um ticket vindo do GLPI via n8n.
    
    Endpoint: POST /api/glpi/webhook/ticket/
    Fluxo: GLPI → n8n → Django
    
    Requer autenticação por token no header:
    Authorization: Token <token_aqui>
    
    Valida o payload, limpa o HTML do conteúdo e salva/atualiza o ticket
    no banco de dados local.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = GlpiWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cleaned_content = clean_html_content(data["content"])

        ticket, _ = Ticket.objects.update_or_create(
            id=data["id"],
            defaults={
                "date_creation": data["date_creation"],
                "user_recipient_id": data["user_recipient_id"],
                "user_recipient_name": data["user_recipient_name"],
                "location": data.get("location") or "",
                "name": data["name"],
                "content_html": cleaned_content,
                "category_name": data.get("category_name") or "",
                "entity_id": data.get("entity_id"),
                "entity_name": data.get("entity_name") or "",
                "team_assigned_id": data.get("team_assigned_id"),
                "team_assigned_name": data.get("team_assigned_name") or "",
                "last_glpi_update": timezone.now(),
                "raw_payload": request.data
            }
        )

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
            glpi_ticket_id = data.get("glpi_ticket_id")
            
            if glpi_ticket_id:
                try:
                    ticket = Ticket.objects.get(id=glpi_ticket_id)
                    suggested_category = GlpiCategory.objects.filter(
                        glpi_id=result["suggested_category_id"]
                    ).first()
                    
                    if suggested_category:
                        ticket.category = suggested_category
                        ticket.category_name = result["suggested_category_name"]
                        ticket.classification_method = result.get("classification_method")
                        ticket.classification_confidence = result.get("confidence")
                        ticket.save()
                except Ticket.DoesNotExist:
                    logger.warning(f"Ticket {glpi_ticket_id} não encontrado ao atualizar categoria")
                except Exception as e:
                    logger.error(f"Erro ao atualizar ticket {glpi_ticket_id}: {str(e)}")
            
            response_serializer = TicketClassificationResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            glpi_ticket_id = data.get("glpi_ticket_id")
            suggestion_created = False
            
            if glpi_ticket_id:
                try:
                    ticket = Ticket.objects.get(id=glpi_ticket_id)
                    ticket.glpi_status = "Aprovação"
                    ticket.save()
                    
                    suggestion = CategorySuggestion.objects.filter(
                        ticket=ticket,
                        status='pending'
                    ).order_by('-created_at').first()
                    
                    if suggestion:
                        suggestion_created = True
                except Ticket.DoesNotExist:
                    logger.warning(f"Ticket {glpi_ticket_id} não encontrado ao definir status")
                except Exception as e:
                    logger.error(f"Erro ao processar ticket {glpi_ticket_id}: {str(e)}")
            
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
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            queryset = queryset.filter(status='pending')
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = []
        for suggestion in queryset:
            data.append({
                'id': suggestion.id,
                'suggested_path': suggestion.suggested_path,
                'ticket_id': suggestion.ticket.id,
                'ticket_title': suggestion.ticket_title,
                'ticket_content': suggestion.ticket_content[:500] if suggestion.ticket_content else '',
                'status': suggestion.status,
                'created_at': suggestion.created_at,
                'reviewed_at': suggestion.reviewed_at,
                'reviewed_by': suggestion.reviewed_by,
                'notes': suggestion.notes
            })
        return Response(data, status=status.HTTP_200_OK)


class CategorySuggestionApproveView(APIView):
    """
    Aprova uma sugestão de categoria.
    
    Endpoint: POST /api/category-suggestions/<id>/approve/
    Requer autenticação por token.
    
    Marca a sugestão como aprovada. A categoria sugerida deve ser criada
    manualmente no GLPI e depois sincronizada via endpoint de sincronização
    de categorias (/api/glpi/categories/sync-from-api/).
    
    Payload opcional:
        {
            "notes": "Notas sobre a aprovação"
        }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            suggestion = CategorySuggestion.objects.get(pk=pk)
        except CategorySuggestion.DoesNotExist:
            return Response({"detail": "Sugestão não encontrada"}, status=status.HTTP_404_NOT_FOUND)
        
        if suggestion.status != 'pending':
            return Response(
                {"detail": f"Sugestão já foi {suggestion.get_status_display().lower()}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        suggestion.status = 'approved'
        suggestion.reviewed_at = timezone.now()
        suggestion.reviewed_by = request.user.username if request.user.is_authenticated else 'api'
        suggestion.notes = request.data.get('notes', '')
        suggestion.save()
        
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
    
    Marca a sugestão como rejeitada, indicando que a categoria sugerida
    não deve ser criada no GLPI.
    
    Payload opcional:
        {
            "notes": "Motivo da rejeição"
        }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            suggestion = CategorySuggestion.objects.get(pk=pk)
        except CategorySuggestion.DoesNotExist:
            return Response({"detail": "Sugestão não encontrada"}, status=status.HTTP_404_NOT_FOUND)
        
        if suggestion.status != 'pending':
            return Response(
                {"detail": f"Sugestão já foi {suggestion.get_status_display().lower()}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        suggestion.status = 'rejected'
        suggestion.reviewed_at = timezone.now()
        suggestion.reviewed_by = request.user.username if request.user.is_authenticated else 'api'
        suggestion.notes = request.data.get('notes', '')
        suggestion.save()
        
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
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        
        if not title:
            return Response(
                {"detail": "Campo 'title' é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
        
        path_parts = [part.strip() for part in suggested_path.split('>') if part.strip()]
        ticket_type, ticket_type_label = determine_ticket_type(path_parts)
        
        return Response(
            {
                "suggested_path": suggested_path,
                "ticket_type": ticket_type,
                "ticket_type_label": ticket_type_label,
                "classification_method": "new_suggestion",
                "note": "Nova sugestão gerada (categoria não encontrada). Esta é apenas uma prévia."
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
            ticket_id = int(ticket_id)
            rating = int(rating)
        except (ValueError, TypeError):
            return render(request, 'satisfaction_survey/success.html', {
                'error': 'Parâmetros inválidos.',
                'rating': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if rating < 1 or rating > 5:
            return render(request, 'satisfaction_survey/success.html', {
                'error': 'Rating deve ser entre 1 e 5.',
                'rating': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            return render(request, 'satisfaction_survey/success.html', {
                'error': f'Ticket #{ticket_id} não encontrado.',
                'rating': None
            }, status=status.HTTP_404_NOT_FOUND)
        
        existing_survey = SatisfactionSurvey.objects.filter(ticket=ticket).first()
        provided_token = request.GET.get('token', '').strip()
        
        if existing_survey:
            if existing_survey.token:
                if not provided_token or not existing_survey.is_token_valid(provided_token):
                    return render(request, 'satisfaction_survey/success.html', {
                        'error': 'Token inválido ou expirado. Esta pesquisa já foi respondida.',
                        'rating': None
                    }, status=status.HTTP_403_FORBIDDEN)
            
            existing_survey.rating = rating
            if not existing_survey.token:
                existing_survey.generate_token()
                existing_survey.save(update_fields=['rating'])
            else:
                existing_survey.save()
            survey = existing_survey
        else:
            survey = SatisfactionSurvey.objects.create(
                ticket=ticket,
                rating=rating,
                comment=''
            )
            survey.generate_token()
        
        comment = request.GET.get('comment', '').strip()
        if comment:
            survey.comment = comment
            survey.save()
        
        _notify_n8n_survey(ticket_id, rating, survey.comment)
        
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
        try:
            ticket_id = int(ticket_id)
        except (ValueError, TypeError):
            return render(request, 'satisfaction_survey/comment.html', {
                'error': 'ID do ticket inválido.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            return render(request, 'satisfaction_survey/comment.html', {
                'error': f'Ticket #{ticket_id} não encontrado.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        survey = SatisfactionSurvey.objects.filter(ticket=ticket).first()
        provided_token = request.GET.get('token', '').strip()
        
        if survey and survey.token:
            if not provided_token or not survey.is_token_valid(provided_token):
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
        try:
            ticket_id = int(ticket_id)
        except (ValueError, TypeError):
            return render(request, 'satisfaction_survey/comment.html', {
                'error': 'ID do ticket inválido.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            return render(request, 'satisfaction_survey/comment.html', {
                'error': f'Ticket #{ticket_id} não encontrado.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        comment = request.POST.get('comment', '').strip()
        provided_token = request.POST.get('token', request.GET.get('token', '')).strip()
        
        survey = SatisfactionSurvey.objects.filter(ticket=ticket).first()
        
        if survey and survey.token:
            if not provided_token or not survey.is_token_valid(provided_token):
                return render(request, 'satisfaction_survey/comment.html', {
                    'error': 'Token inválido ou expirado. Esta pesquisa já foi respondida.',
                    'ticket': ticket,
                    'survey': survey
                }, status=status.HTTP_403_FORBIDDEN)
        
        if not survey:
            survey = SatisfactionSurvey.objects.create(
                ticket=ticket,
                rating=3,
                comment=comment
            )
            survey.generate_token()
        else:
            survey.comment = comment
            survey.save()
        
        _notify_n8n_survey(ticket_id, survey.rating, comment)
        
        return render(request, 'satisfaction_survey/success.html', {
            'rating': survey.rating,
            'ticket_id': ticket_id,
            'ticket': ticket,
            'has_comment': True,
            'comment': comment,
            'token': survey.token
        })