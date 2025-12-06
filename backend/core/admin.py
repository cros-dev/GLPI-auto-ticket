from django.contrib import admin
from django.utils.html import mark_safe
from django.utils import timezone
from .models import GlpiCategory, Ticket, Attachment, CategorySuggestion
from .services import get_category_path

class Level1Filter(admin.SimpleListFilter):
    """
    Filtro customizado para filtrar categorias por nível 1 (categoria raiz).
    
    Permite filtrar todas as categorias que pertencem a uma categoria raiz específica,
    incluindo todas as suas subcategorias em qualquer nível hierárquico.
    """
    title = 'Nível 1'
    parameter_name = 'level1'
    
    def _get_effective_level1(self, category):
        """
        Retorna o nome do nível 1 lógico usado nos filtros.
        Ignora prefixos como "TI" e usa o segundo nível quando disponível.
        """
        path = get_category_path(category)
        if len(path) > 1:
            return path[1]
        return path[0] if path else None
    
    def lookups(self, request, model_admin):
        """
        Retorna lista de categorias do nível 1 (raiz) para o filtro.
        
        Args:
            request: Requisição HTTP
            model_admin: Instância do ModelAdmin
            
        Returns:
            list: Lista de tuplas (id, nome) das categorias raiz
        """
        level_names = []
        seen = set()
        for category in GlpiCategory.objects.all().order_by('name'):
            name = self._get_effective_level1(category)
            if name and name not in seen:
                seen.add(name)
                level_names.append((name, name))
        return level_names
    
    def queryset(self, request, queryset):
        """
        Filtra as categorias baseado no nível 1 selecionado.
        
        Args:
            request: Requisição HTTP
            queryset: QuerySet inicial de categorias
            
        Returns:
            QuerySet: QuerySet filtrado contendo apenas categorias do nível 1 selecionado
        """
        if self.value():
            category_ids = []
            for cat in queryset:
                if self._get_effective_level1(cat) == self.value():
                    category_ids.append(cat.id)
            return queryset.filter(id__in=category_ids)
        return queryset

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    Configuração do admin para o modelo Ticket.
    
    Exibe tickets recebidos do GLPI via webhook, com conteúdo limpo (sem HTML)
    e campos organizados em seções.
    """
    list_display = ('id', 'name', 'category_name', 'category_suggestion_display', 'classification_method', 'classification_confidence', 'created_at')
    list_filter = ('created_at', 'classification_method', 'classification_confidence')
    search_fields = ('name', 'content_html', 'id') 
    
    readonly_fields = (
        'id',
        'name', 
        'category_name', 
        'category_suggestion_display',
        'classification_method',
        'classification_confidence',
        'user_recipient_name', 
        'location',
        'content_text_clean', 
        'created_at', 
        'updated_at', 
        'last_glpi_update', 
        'raw_payload'
    )

    fieldsets = (
        ('Dados do Ticket', {
            'fields': (
                'id', 
                'name',                
                'content_text_clean',
                'category_name', 
                'category_suggestion_display',
                'classification_method',
                'classification_confidence',
                'user_recipient_name', 
                'location'
            )
        }),
        ('Dados Brutos (Debug)', {
            'fields': ('content_html', 'raw_payload', 'created_at', 'updated_at'),
            'classes': ('collapse',), 
        }),
    )

    def content_text_clean(self, obj):
        """
        Exibe o conteúdo limpo do ticket formatado para HTML.
        
        O conteúdo já vem limpo (sem HTML) do webhook, apenas formata
        quebras de linha para exibição correta no admin.
        
        Args:
            obj: Instância de Ticket
            
        Returns:
            str: Conteúdo formatado em HTML ou "-" se vazio
        """
        if not obj.content_html:
            return "-"
        return mark_safe(obj.content_html.replace('\n', '<br>'))

    content_text_clean.short_description = "Descrição"
    
    def category_suggestion_display(self, obj):
        """
        Exibe sugestão de categoria pendente para este ticket.
        
        Args:
            obj: Instância de Ticket
            
        Returns:
            str: Caminho sugerido com link para a sugestão ou "-" se não houver
        """
        if not obj.id:
            return "-"
        
        suggestion = CategorySuggestion.objects.filter(
            ticket=obj,
            status='pending'
        ).order_by('-created_at').first()
        
        if suggestion:
            url = f"/admin/core/categorysuggestion/{suggestion.id}/change/"
            return mark_safe(
                f'<a href="{url}" style="color: #417690; font-weight: bold;">{suggestion.suggested_path}</a>'
            )
        return "-"
    
    category_suggestion_display.short_description = "Category Suggestion"

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """
    Configuração do admin para o modelo Attachment.
    
    Exibe anexos vinculados a tickets, com metadados e download do arquivo.
    """
    list_display = ('id', 'name', 'ticket', 'mime_type', 'size')
    readonly_fields = ('data',)
    
@admin.register(GlpiCategory)
class GlpiCategoryAdmin(admin.ModelAdmin):
    """
    Configuração do admin para o modelo GlpiCategory.
    
    Exibe categorias GLPI em formato hierárquico com colunas separadas
    para cada nível (Nível 1, 2, 3, 4, 5) facilitando a visualização.
    """
    list_display = ('id_display', 'level_1', 'level_2', 'level_3', 'level_4', 'level_5', 'level_6')
    list_filter = (Level1Filter,)
    search_fields = ('name',)
    ordering = ('glpi_id',)
    list_per_page = 100
    
    def id_display(self, obj):
        """
        Exibe o ID GLPI da categoria.
        
        Args:
            obj: Instância de GlpiCategory
            
        Returns:
            int: ID GLPI da categoria
        """
        return obj.glpi_id
    id_display.short_description = 'ID'
    id_display.admin_order_field = 'glpi_id'
    
    def level_1(self, obj):
        """
        Retorna o nome da categoria do nível 1 (raiz) da hierarquia.
        
        Args:
            obj: Instância de GlpiCategory
            
        Returns:
            str: Nome da categoria raiz ou '-' se não houver
        """
        path = get_category_path(obj)
        return path[0] if len(path) > 0 else '-'
    level_1.short_description = 'Nível 1'
    
    def level_2(self, obj):
        """
        Retorna o nome da categoria do nível 2 da hierarquia.
        
        Args:
            obj: Instância de GlpiCategory
            
        Returns:
            str: Nome da categoria do nível 2 ou '-' se não houver
        """
        path = get_category_path(obj)
        return path[1] if len(path) > 1 else '-'
    level_2.short_description = 'Nível 2'
    
    def level_3(self, obj):
        """
        Retorna o nome da categoria do nível 3 da hierarquia.
        
        Args:
            obj: Instância de GlpiCategory
            
        Returns:
            str: Nome da categoria do nível 3 ou '-' se não houver
        """
        path = get_category_path(obj)
        return path[2] if len(path) > 2 else '-'
    level_3.short_description = 'Nível 3'
    
    def level_4(self, obj):
        """
        Retorna o nome da categoria do nível 4 da hierarquia.
        
        Args:
            obj: Instância de GlpiCategory
            
        Returns:
            str: Nome da categoria do nível 4 ou '-' se não houver
        """
        path = get_category_path(obj)
        return path[3] if len(path) > 3 else '-'
    level_4.short_description = 'Nível 4'
    
    def level_5(self, obj):
        """
        Retorna o nome da categoria do nível 5 da hierarquia.
        """
        path = get_category_path(obj)
        return path[4] if len(path) > 4 else '-'
    level_5.short_description = 'Nível 5'

    def level_6(self, obj):
        """
        Retorna o nome da categoria do nível 6 da hierarquia.
        """
        path = get_category_path(obj)
        return path[5] if len(path) > 5 else '-'
    level_6.short_description = 'Nível 6'


@admin.register(CategorySuggestion)
class CategorySuggestionAdmin(admin.ModelAdmin):
    """
    Configuração do admin para sugestões de categorias.
    
    Exibe sugestões geradas pela IA quando não encontra categoria exata,
    permitindo revisão e aprovação manual.
    """
    list_display = ('id', 'suggested_path', 'ticket_link', 'status', 'created_at', 'reviewed_at')
    list_filter = ('status', 'created_at', 'reviewed_at')
    search_fields = ('suggested_path', 'ticket_title', 'ticket__id')
    readonly_fields = (
        'ticket',
        'ticket_title',
        'ticket_content_display',
        'suggested_path',
        'created_at',
        'updated_at',
        'reviewed_at',
        'reviewed_by'
    )
    actions = ['approve_suggestions', 'reject_suggestions']
    
    fieldsets = (
        ('Sugestão', {
            'fields': (
                'suggested_path',
                'status',
                'notes'
            )
        }),
        ('Ticket Relacionado', {
            'fields': (
                'ticket',
                'ticket_title',
                'ticket_content_display'
            )
        }),
        ('Revisão', {
            'fields': (
                'reviewed_at',
                'reviewed_by'
            )
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def ticket_link(self, obj):
        """Exibe link para o ticket relacionado."""
        return mark_safe(f'<a href="/admin/core/ticket/{obj.ticket.id}/change/">Ticket #{obj.ticket.id}</a>')
    ticket_link.short_description = 'Ticket'
    
    def ticket_content_display(self, obj):
        """Exibe conteúdo do ticket formatado."""
        if not obj.ticket_content:
            return "-"
        return mark_safe(obj.ticket_content.replace('\n', '<br>'))
    ticket_content_display.short_description = 'Conteúdo do Ticket'
    
    def approve_suggestions(self, request, queryset):
        """Aprova sugestões selecionadas."""
        count = 0
        for suggestion in queryset.filter(status='pending'):
            suggestion.status = 'approved'
            suggestion.reviewed_at = timezone.now()
            suggestion.reviewed_by = request.user.username
            suggestion.save()
            count += 1
        self.message_user(request, f'{count} sugestão(ões) aprovada(s).')
    approve_suggestions.short_description = 'Aprovar sugestões selecionadas'
    
    def reject_suggestions(self, request, queryset):
        """Rejeita sugestões selecionadas."""
        count = 0
        for suggestion in queryset.filter(status='pending'):
            suggestion.status = 'rejected'
            suggestion.reviewed_at = timezone.now()
            suggestion.reviewed_by = request.user.username
            suggestion.save()
            count += 1
        self.message_user(request, f'{count} sugestão(ões) rejeitada(s).')
    reject_suggestions.short_description = 'Rejeitar sugestões selecionadas'