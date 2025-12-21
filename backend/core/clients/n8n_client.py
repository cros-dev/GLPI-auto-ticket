"""
Cliente para integração com n8n via webhooks.

Centraliza notificações para n8n, incluindo:
- Pesquisas de satisfação
- Aprovações/rejeições de categorias
- Tratamento de erros e timeouts
"""
import logging
from typing import Optional, Dict, Any
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class N8nClient:
    """
    Cliente para comunicação com n8n via webhooks.
    
    Encapsula toda lógica de notificações para n8n.
    """
    
    def __init__(
        self,
        survey_webhook_url: Optional[str] = None,
        category_approval_webhook_url: Optional[str] = None
    ):
        """
        Inicializa o cliente n8n.
        
        Args:
            survey_webhook_url: URL do webhook para pesquisas de satisfação
            category_approval_webhook_url: URL do webhook para aprovações de categorias
        """
        self.survey_webhook_url = (
            survey_webhook_url or 
            getattr(settings, 'N8N_SURVEY_RESPONSE_WEBHOOK_URL', None)
        )
        self.category_approval_webhook_url = (
            category_approval_webhook_url or 
            getattr(settings, 'N8N_CATEGORY_APPROVAL_WEBHOOK_URL', None)
        )
    
    def notify_survey_response(
        self,
        ticket_id: int,
        rating: int,
        comment: Optional[str] = None
    ) -> bool:
        """
        Notifica n8n sobre resposta de pesquisa de satisfação.
        
        Args:
            ticket_id: ID do ticket
            rating: Nota de satisfação (1-5)
            comment: Comentário opcional
            
        Returns:
            bool: True se notificação foi enviada com sucesso, False caso contrário
        """
        if not self.survey_webhook_url:
            logger.debug("N8N_SURVEY_RESPONSE_WEBHOOK_URL não configurado, notificação ignorada")
            return False
        
        try:
            payload = {
                'ticket_id': ticket_id,
                'rating': rating,
                'comment': comment or '',
                'type': 'satisfaction-survey-update'
            }
            
            response = requests.post(
                self.survey_webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Erro ao notificar n8n sobre pesquisa de satisfação: {str(e)}")
            return False
    
    def notify_category_approval(
        self,
        suggestion_id: int,
        ticket_id: int,
        suggested_path: str,
        parent_glpi_id: int,
        category_name: str,
        status: str,
        notes: Optional[str] = None,
        reviewed_by: Optional[str] = None,
        reviewed_at: Optional[str] = None,
        is_incident: int = 0,
        is_request: int = 0,
        is_problem: int = 0,
        is_change: int = 0
    ) -> bool:
        """
        Notifica n8n sobre aprovação/rejeição de sugestão de categoria.
        
        Args:
            suggestion_id: ID da sugestão no Django
            ticket_id: ID do ticket relacionado
            suggested_path: Caminho sugerido da categoria (hierárquico)
            parent_glpi_id: ID do pai no GLPI (itilcategories_id)
            category_name: Nome do último nível da categoria a ser criada
            status: Status final da sugestão ('approved' | 'rejected')
            notes: Notas opcionais do revisor
            reviewed_by: Usuário que revisou
            reviewed_at: Data/hora da revisão (ISO)
            is_incident: Se a categoria é para incidentes (0 ou 1)
            is_request: Se a categoria é para requisições (0 ou 1)
            is_problem: Se a categoria é para problemas (0 ou 1)
            is_change: Se a categoria é para mudanças (0 ou 1)
            
        Returns:
            bool: True se notificação foi enviada com sucesso, False caso contrário
        """
        if not self.category_approval_webhook_url:
            logger.debug("N8N_CATEGORY_APPROVAL_WEBHOOK_URL não configurado, notificação ignorada")
            return False
        
        try:
            payload = {
                'suggestion_id': suggestion_id,
                'ticket_id': ticket_id,
                'suggested_path': suggested_path,
                'parent_glpi_id': parent_glpi_id,
                'category_name': category_name,
                'status': status,
                'notes': notes or '',
                'reviewed_by': reviewed_by or '',
                'reviewed_at': reviewed_at,
                'type': 'category-suggestion-review',
                'is_incident': is_incident,
                'is_request': is_request,
                'is_problem': is_problem,
                'is_change': is_change
            }
            
            response = requests.post(
                self.category_approval_webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Erro ao notificar n8n sobre aprovação de categoria: {str(e)}")
            return False

