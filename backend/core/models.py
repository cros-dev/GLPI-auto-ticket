"""
Modelos de dados para o sistema de tickets GLPI.

Este módulo contém os modelos principais:
- GlpiCategory: Categorias GLPI para classificação de tickets
- Ticket: Tickets recebidos do GLPI via webhook
- Attachment: Anexos vinculados aos tickets
"""
from django.db import models


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
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children'
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
        null=True, blank=True,
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
        GlpiCategory, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="tickets"
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
        max_length=50, null=True, blank=True,
        help_text="Status atual do ticket no GLPI"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_glpi_update = models.DateTimeField(
        null=True, blank=True,
        help_text="Última vez que o GLPI atualizou esse ticket"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ticket GLPI'
        verbose_name_plural = 'Tickets GLPI'

    def __str__(self):
        return f"Ticket GLPI #{self.id}"


class Attachment(models.Model):
    """
    Anexo recebido do GLPI via webhook.
    
    Armazena arquivos binários vinculados a tickets, incluindo metadados
    como nome, tipo MIME e tamanho.
    """
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')

    name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size = models.IntegerField()
    data = models.BinaryField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Anexo GLPI'
        verbose_name_plural = 'Anexos GLPI'

    def __str__(self):
        return self.name
