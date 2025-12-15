"""
Modelos de dados para o sistema de tickets GLPI.

Este módulo contém os modelos principais:
- GlpiCategory: Categorias GLPI para classificação de tickets
- Ticket: Tickets recebidos do GLPI via webhook
- CategorySuggestion: Sugestões de categorias geradas pela IA para revisão manual
- SatisfactionSurvey: Pesquisas de satisfação respondidas pelos usuários
"""
import secrets
from datetime import timedelta
from django.db import models
from django.utils import timezone


class GlpiCategory(models.Model):
    """
    Categoria GLPI armazenada localmente para uso nas classificações.
    
    Representa uma categoria hierárquica do GLPI, permitindo classificação
    automática de tickets através de palavras-chave.
    """
    
    glpi_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    full_path = models.CharField(
        max_length=1024,
        blank=True,
        default='',
        help_text="Caminho completo (ex.: 'TI > Requisição > Acesso')"
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Categoria GLPI'
        verbose_name_plural = 'Categorias GLPI'

    def __str__(self):
        return f"{self.name} ({self.glpi_id})"


class Ticket(models.Model):
    """
    Ticket criado pelo webhook do GLPI ou pelo processamento interno do sistema.
    
    Armazena informações de tickets recebidos do GLPI via n8n, incluindo
    conteúdo limpo (sem HTML), metadados do usuário, categoria e equipe atribuída.
    
    O ID do ticket é o mesmo ID do GLPI (primary key).
    """
    
    # ID do ticket (mesmo ID do GLPI)
    id = models.IntegerField(
        primary_key=True,
        verbose_name='ID do Ticket GLPI'
    )

    raw_payload = models.JSONField(
        null=True,
        blank=True,
        help_text="Payload bruto vindo do GLPI para auditoria"
    )

    # Dados principais
    name = models.CharField(max_length=255)
    content_html = models.TextField(null=True, blank=True)
    date_creation = models.DateTimeField(null=True, blank=True)

    # Usuário e localização
    user_recipient_id = models.IntegerField(null=True, blank=True)
    user_recipient_name = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)

    # Categoria
    category = models.ForeignKey(
        GlpiCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets"
    )
    category_name = models.CharField(max_length=255, null=True, blank=True)
    classification_method = models.CharField(max_length=50, null=True, blank=True)
    classification_confidence = models.CharField(max_length=50, null=True, blank=True)

    # Entidade / organização
    entity_id = models.IntegerField(null=True, blank=True)
    entity_name = models.CharField(max_length=255, null=True, blank=True)

    # Equipe atribuída
    team_assigned_id = models.IntegerField(null=True, blank=True)
    team_assigned_name = models.CharField(max_length=255, null=True, blank=True)

    # Status do GLPI
    glpi_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Status atual do ticket no GLPI"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_glpi_update = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Última vez que o GLPI atualizou esse ticket"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ticket GLPI'
        verbose_name_plural = 'Tickets GLPI'

    def __str__(self):
        return f"Ticket GLPI #{self.id}"


class CategorySuggestion(models.Model):
    """
    Sugestão de categoria gerada pela IA quando não encontra categoria exata.
    
    Armazena sugestões de novas categorias para revisão manual antes de criar
    no GLPI e sincronizar via CSV.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('approved', 'Aprovada'),
        ('rejected', 'Rejeitada'),
    ]
    
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='category_suggestions',
        help_text="Ticket que gerou esta sugestão"
    )
    
    suggested_path = models.CharField(
        max_length=1024,
        help_text="Caminho completo sugerido (ex.: 'TI > Requisição > Administrativo > Montagem de Setup > Transmissão/Vídeo Conferência')"
    )
    
    ticket_title = models.CharField(
        max_length=255,
        help_text="Título do ticket para contexto"
    )
    
    ticket_content = models.TextField(
        blank=True,
        help_text="Conteúdo do ticket para contexto"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Status da sugestão"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Notas adicionais sobre a sugestão"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    reviewed_by = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sugestão de Categoria'
        verbose_name_plural = 'Sugestões de Categorias'

    def __str__(self):
        return f"{self.suggested_path} (Ticket #{self.ticket.id})"


class SatisfactionSurvey(models.Model):
    """
    Pesquisa de satisfação respondida pelo usuário sobre o atendimento recebido.
    
    Armazena respostas de pesquisas de satisfação coletadas via botões diretos
    no e-mail enviado pelo GLPI após o fechamento/resolução de um ticket.
    """
    
    RATING_CHOICES = [
        (1, '1 - Muito Insatisfeito'),
        (2, '2 - Insatisfeito'),
        (3, '3 - Neutro'),
        (4, '4 - Satisfeito'),
        (5, '5 - Muito Satisfeito'),
    ]
    
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='satisfaction_surveys',
        help_text="Ticket relacionado à pesquisa de satisfação"
    )
    
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        help_text="Nota de satisfação do usuário (1 a 5)"
    )
    
    comment = models.TextField(
        blank=True,
        help_text="Comentário opcional do usuário sobre o atendimento"
    )
    
    token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Token único de segurança para validar a pesquisa (gerado na primeira requisição)"
    )
    
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data de expiração do token (padrão: 30 dias após criação)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def generate_token(self):
        """
        Gera um token único seguro para a pesquisa.
        
        Returns:
            str: Token único gerado
        """
        if not self.token:
            self.token = secrets.token_urlsafe(32)
            # Expira em 30 dias
            self.token_expires_at = timezone.now() + timedelta(days=30)
            self.save(update_fields=['token', 'token_expires_at'])
        return self.token
    
    def is_token_valid(self, provided_token):
        """
        Valida se o token fornecido é válido e não expirou.
        
        Args:
            provided_token: Token fornecido pelo usuário
            
        Returns:
            bool: True se o token é válido, False caso contrário
        """
        if not self.token or not provided_token:
            return False
        
        if self.token != provided_token:
            return False
        
        # Verifica expiração
        if self.token_expires_at and timezone.now() > self.token_expires_at:
            return False
        
        return True
    
    def reset_token(self):
        """
        Reseta o token da pesquisa, permitindo nova resposta.
        
        Remove o token atual completamente. Um novo token será gerado
        automaticamente na próxima requisição do usuário.
        
        Returns:
            None
        """
        self.token = None
        self.token_expires_at = None
        self.save(update_fields=['token', 'token_expires_at'])
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Pesquisa de Satisfação'
        verbose_name_plural = 'Pesquisas de Satisfação'
        constraints = [
            models.UniqueConstraint(fields=['ticket'], name='unique_survey_per_ticket')
        ]
    
    def __str__(self):
        return f"Pesquisa Ticket #{self.ticket.id} - {self.rating}/5 ({self.created_at.strftime('%d/%m/%Y %H:%M')})"
