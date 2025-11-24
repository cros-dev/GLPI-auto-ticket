"""
Views da API REST para gerenciamento de tickets e categorias GLPI.

Este módulo contém todas as views que expõem endpoints da API:
- Categorias: listagem e sincronização
- Tickets: webhook, listagem, detalhe e classificação
- Anexos: download de arquivos
"""
import csv
import io
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse, Http404
from django.utils import timezone
from django.db import models

from .models import GlpiCategory, Ticket, Attachment
from .serializers import (
    GlpiCategorySerializer, 
    TicketSerializer, 
    GlpiWebhookSerializer,
    TicketClassificationSerializer,
    TicketClassificationResponseSerializer
)
from .utils import clean_html_content
from .services import classify_ticket 


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


class GlpiCategorySyncView(APIView):
    """
    Sincroniza categorias GLPI recebidas via requisição HTTP.
    
    Endpoint: POST /api/glpi/categories/sync/
    Realiza upsert (cria novas ou atualiza existentes) processando automaticamente
    a hierarquia a partir do formato hierárquico.
    
    Aceita dois formatos:
    1. JSON (formato hierárquico):
       ["Requisição", "Requisição > Acesso", "Requisição > Acesso > AD", ...]
    
    2. CSV (arquivo com coluna "Nome completo"):
       Envie um arquivo CSV com a coluna "Nome completo" contendo o caminho hierárquico.
    
    Processa automaticamente a hierarquia e cria os relacionamentos parent/child.
    """
    def post(self, request):
        # Verifica se é upload de arquivo CSV
        if 'file' in request.FILES:
            categories = self._parse_csv(request.FILES['file'])
        else:
            # Aceita lista direta ou dentro de objeto com chave "categories"
            if isinstance(request.data, list):
                categories = request.data
            else:
                categories = request.data.get("categories") or request.data
        
        if not isinstance(categories, list):
            return Response(
                {"detail": "Expected a list of category paths (strings) or CSV file"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not categories:
            return Response(
                {"detail": "Categories list cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(categories[0], str):
            return Response(
                {"detail": "Expected list of strings in hierarchical format (e.g., 'Nível 1 > Nível 2')"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = self._process_categories(categories)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _parse_csv(self, file):
        """
        Parseia arquivo CSV e extrai a coluna "Nome completo".
        
        Args:
            file: Arquivo CSV enviado
            
        Returns:
            list: Lista de strings com os caminhos hierárquicos das categorias
            
        Raises:
            ValueError: Se houver erro ao processar o CSV
        """
        try:
            # Lê o arquivo como texto
            content = file.read()
            if isinstance(content, bytes):
                # Remove BOM se houver (utf-8-sig)
                content = content.decode('utf-8-sig')
            
            # Parseia o CSV
            csv_reader = csv.DictReader(io.StringIO(content))
            categories = []
            
            # Encontra a coluna "Nome completo" (case-insensitive)
            column_name = None
            for key in csv_reader.fieldnames or []:
                if key.lower().strip() == 'nome completo':
                    column_name = key
                    break
            
            if not column_name:
                raise ValueError("Coluna 'Nome completo' não encontrada no CSV")
            
            for row in csv_reader:
                full_name = row.get(column_name, '').strip()
                if full_name:
                    categories.append(full_name)
            
            return categories
            
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Erro ao processar CSV: {str(e)}")
    
    def _process_categories(self, categories):
        """
        Processa lista de categorias e cria/atualiza no banco.
        
        Args:
            categories: Lista de strings com caminhos hierárquicos
            
        Returns:
            dict: Estatísticas de criação (created, total)
        """
        created_categories = {}
        created_count = 0
        
        # Calcula o próximo glpi_id disponível uma única vez
        max_glpi_id = GlpiCategory.objects.aggregate(
            max_id=models.Max('glpi_id')
        )['max_id'] or 0
        next_glpi_id = max_glpi_id + 1

        for category_path in categories:
            if not category_path or not category_path.strip():
                continue
                
            parts = [p.strip() for p in category_path.split('>') if p.strip()]
            if not parts:
                continue
            
            current_path = []
            parent = None
            
            for category_name in parts:
                current_path.append(category_name)
                full_path = ' > '.join(current_path)
                
                if full_path in created_categories:
                    parent = created_categories[full_path]
                else:
                    # Verifica se já existe no banco pelo nome e parent
                    existing = GlpiCategory.objects.filter(
                        name=category_name,
                        parent=parent
                    ).first()
                    
                    if existing:
                        category = existing
                    else:
                        # Garante que o glpi_id seja único
                        while GlpiCategory.objects.filter(glpi_id=next_glpi_id).exists():
                            next_glpi_id += 1
                        
                        category = GlpiCategory.objects.create(
                            glpi_id=next_glpi_id,
                            name=category_name,
                            parent=parent
                        )
                        created_count += 1
                        next_glpi_id += 1
                    
                    created_categories[full_path] = category
                    parent = category

        return {
            "created": created_count,
            "total": len(created_categories)
        }


# =========================================================
# 2. RECEBE WEBHOOK DO N8N (TICKET DO GLPI)
# =========================================================

class GlpiWebhookView(APIView):
    """
    Recebe um ticket vindo do GLPI via n8n.
    
    Endpoint: POST /api/glpi/webhook/ticket/
    Fluxo: GLPI → n8n → Django
    
    Valida o payload, limpa o HTML do conteúdo e salva/atualiza o ticket
    no banco de dados local.
    """
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
                "category_name": data.get("category_name", ""),
                "entity_id": data["entity_id"],
                "entity_name": data["entity_name"],
                "team_assigned_id": data["team_assigned_id"],
                "team_assigned_name": data["team_assigned_name"],
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
# 4. DOWNLOAD DE ANEXOS
# =========================================================

class AttachmentDownloadView(APIView):
    """
    Faz download do arquivo binário do anexo armazenado.
    
    Endpoint: GET /api/attachments/<id>/download/
    Requer autenticação por token.
    Retorna o arquivo binário com o tipo MIME correto e nome do arquivo.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            attachment = Attachment.objects.get(pk=pk)
        except Attachment.DoesNotExist:
            raise Http404("Attachment not found")

        response = FileResponse(
            attachment.data,
            content_type=attachment.mime_type or "application/octet-stream"
        )
        response["Content-Disposition"] = f'attachment; filename="{attachment.name}"'
        return response


# =========================================================
# 5. ENDPOINT PARA O N8N DEFINIR GLPI_ID
# =========================================================

class SetGlpiIdView(APIView):
    """
    Atualiza campos adicionais do ticket após criação/atualização no GLPI.
    
    Endpoint: PATCH /api/tickets/<id>/set-glpi-id/
    Chamado pelo n8n após criar ou atualizar o ticket no GLPI.
    O ID do ticket já é o mesmo do GLPI (primary key), então este endpoint
    serve apenas para atualizar campos adicionais como status.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            ticket = Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({"detail": "Ticket not found"}, status=404)

        status_update = request.data.get("status")
        glpi_updates = request.data.get("glpi_updates")

        if status_update:
            ticket.glpi_status = status_update

        if glpi_updates:
            # Se houver outros campos para atualizar no futuro
            pass

        ticket.save()

        return Response(
            {"detail": "Updated", "ticket": TicketSerializer(ticket).data}
        )


# =========================================================
# 6. CLASSIFICAÇÃO DE TICKET
# =========================================================

class TicketClassificationView(APIView):
    """
    Classifica um ticket e sugere categoria usando Google Gemini AI (quando disponível) 
    ou classificação simples baseada em palavras-chave como fallback.
    
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
        
        result = classify_ticket(
            title=data["title"],
            content=data.get("content", "")
        )
        
        if result:
            # Atualiza o ticket com a categoria sugerida
            glpi_ticket_id = data.get("glpi_ticket_id")
            
            try:
                ticket = Ticket.objects.get(id=glpi_ticket_id)
                
                # Busca a categoria sugerida
                suggested_category = GlpiCategory.objects.filter(
                    glpi_id=result["suggested_category_id"]
                ).first()
                
                if suggested_category:
                    ticket.category = suggested_category
                    ticket.category_name = result["suggested_category_name"]
                    ticket.save()
                    
            except Ticket.DoesNotExist:
                # Se o ticket não existir, apenas retorna a classificação
                pass
            except Exception:
                # Se houver erro, apenas retorna a classificação
                pass
            
            response_serializer = TicketClassificationResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"detail": "Não foi possível classificar o ticket. Verifique se há categorias cadastradas."},
                status=status.HTTP_400_BAD_REQUEST
            )