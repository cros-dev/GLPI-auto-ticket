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
    Sincroniza categorias GLPI recebidas via upload de arquivo CSV.
    
    Endpoint: POST /api/glpi/categories/sync/
    
    O CSV deve conter obrigatoriamente as colunas:
        - "Nome completo": caminho hierárquico (ex.: "TI > Requisição > Acesso")
        - "ID": identificador inteiro fornecido pelo GLPI
    
    O endpoint executa upsert usando o glpi_id informado, garantindo que o
    relacionamento pai/filho seja recriado no Django exatamente como no GLPI.
    """
    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {"detail": "Envie um arquivo CSV usando o campo 'file'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            categories = self._parse_csv(uploaded_file)
            if not categories:
                return Response(
                    {"detail": "Nenhuma categoria encontrada no CSV."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            result = self._process_categories(categories)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _parse_csv(self, file):
        """
        Parseia arquivo CSV e extrai as colunas "Nome completo" e "ID".
        
        Args:
            file: Arquivo CSV enviado
            
        Returns:
            list: Lista de dicionários contendo caminho completo, partes e glpi_id
            
        Raises:
            ValueError: Se houver erro ao processar o CSV
        """
        try:
            # Lê o arquivo como texto
            content = file.read()
            if isinstance(content, bytes):
                # Remove BOM se houver (utf-8-sig)
                content = content.decode('utf-8-sig')
            
            if not content.strip():
                return []
            
            sample = content[:1024]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=';,')
            except Exception:
                dialect = csv.excel
            
            # Parseia o CSV
            csv_reader = csv.DictReader(io.StringIO(content), dialect=dialect)
            categories = []
            
            if not csv_reader.fieldnames:
                raise ValueError("Cabeçalho do CSV não encontrado.")
            
            normalized_headers = {
                (header or '').lower().strip(): header 
                for header in csv_reader.fieldnames
            }
            
            name_column = normalized_headers.get('nome completo')
            id_column = normalized_headers.get('id')
            
            if not name_column or not id_column:
                raise ValueError("As colunas 'Nome completo' e 'ID' são obrigatórias no CSV.")
            
            seen_ids = set()
            for row in csv_reader:
                full_name = (row.get(name_column) or '').strip()
                raw_id = (row.get(id_column) or '').strip()
                
                if not full_name:
                    continue
                
                if not raw_id:
                    raise ValueError(f"ID ausente para a categoria '{full_name}'.")
                
                try:
                    glpi_id = int(raw_id.replace('"', ''))
                except ValueError:
                    raise ValueError(f"ID inválido '{raw_id}' para a categoria '{full_name}'.")
                
                if glpi_id in seen_ids:
                    raise ValueError(f"ID duplicado '{glpi_id}' encontrado no CSV.")
                seen_ids.add(glpi_id)
                
                parts = [p.strip() for p in full_name.split('>') if p.strip()]
                if not parts:
                    continue
                
                categories.append({
                    "full_path": ' > '.join(parts),
                    "parts": parts,
                    "parent_path": ' > '.join(parts[:-1]) if len(parts) > 1 else '',
                    "glpi_id": glpi_id,
                })
            
            return categories
            
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Erro ao processar CSV: {str(e)}")
    
    def _process_categories(self, categories):
        """
        Processa lista de categorias e cria/atualiza no banco.
        
        Args:
            categories: Lista de dicionários retornados por _parse_csv
            
        Returns:
            dict: Estatísticas de criação/atualização
        """
        created_categories = {}
        created_count = 0
        updated_count = 0
        cache_by_path = {}
        
        sorted_categories = sorted(categories, key=lambda item: len(item["parts"]))
        
        for entry in sorted_categories:
            category_name = entry["parts"][-1]
            parent_path = entry["parent_path"]
            parent = None
            
            if parent_path:
                parent = cache_by_path.get(parent_path)
                if not parent:
                    parent = self._find_existing_by_path(parent_path)
                if not parent:
                    parent_segments = [p.strip() for p in parent_path.split('>') if p.strip()]
                    # Se o caminho pai representa apenas o primeiro nível (ex.: "TI"),
                    # tratamos como raiz (parent=None) permitindo que o CSV use um prefixo comum.
                    if len(parent_segments) > 1:
                        raise ValueError(f"Categoria pai '{parent_path}' não encontrada no CSV ou no banco.")
                    parent = None
            
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
        
        return {
            "created": created_count,
            "updated": updated_count,
            "total": GlpiCategory.objects.count()
        }
    
    def _find_existing_by_path(self, path):
        """
        Busca uma categoria existente no banco percorrendo o caminho informado.
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
                ticket.classification_method = result.get("classification_method")
                ticket.classification_confidence = result.get("confidence")
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
            # Quando não consegue classificar, atualiza o status para "Aprovação" (status 10)
            glpi_ticket_id = data.get("glpi_ticket_id")
            if glpi_ticket_id:
                try:
                    ticket = Ticket.objects.get(id=glpi_ticket_id)
                    ticket.glpi_status = "Aprovação"
                    ticket.save()
                except Ticket.DoesNotExist:
                    pass
                except Exception:
                    pass
            
            return Response(
                {"detail": "Não foi possível classificar o ticket. Verifique se há categorias cadastradas."},
                status=status.HTTP_400_BAD_REQUEST
            )