from django.contrib import admin
from django.utils.html import mark_safe
from django.utils import timezone
from .models import GlpiCategory, Ticket, CategorySuggestion, SatisfactionSurvey, KnowledgeBaseArticle
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
    list_display = ('id', 'name', 'category_name', 'category_suggestion_display', 'satisfaction_survey_display', 'classification_method', 'classification_confidence', 'created_at')
    list_filter = ('created_at', 'classification_method', 'classification_confidence')
    search_fields = ('name', 'content_html', 'id')
    
    readonly_fields = (
        'id',
        'name', 
        'category_name', 
        'category_suggestion_display',
        'satisfaction_survey_display',
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
                'satisfaction_survey_display',
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

    content_text_clean.short_description = 'Descrição'
    
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
            status='pending'  # Valor do choice CATEGORY_SUGGESTION_STATUS_CHOICES
        ).order_by('-created_at').first()
        
        if suggestion:
            url = f"/admin/core/categorysuggestion/{suggestion.id}/change/"
            return mark_safe(
                f'<a href="{url}" style="color: #417690; font-weight: bold;">{suggestion.suggested_path}</a>'
            )
        return "-"
    
    category_suggestion_display.short_description = 'Category Suggestion'
    
    def satisfaction_survey_display(self, obj):
        """
        Exibe pesquisa de satisfação para este ticket.
        
        Args:
            obj: Instância de Ticket
            
        Returns:
            str: Link para a pesquisa ou "-" se não houver
        """
        if not obj.id:
            return "-"
        
        survey = SatisfactionSurvey.objects.filter(ticket=obj).first()
        
        if survey:
            url = f"/admin/core/satisfactionsurvey/{survey.id}/change/"
            return mark_safe(
                f'<a href="{url}" style="color: #417690; font-weight: bold;">Ver Pesquisa</a>'
            )
        return "-"
    
    satisfaction_survey_display.short_description = 'Pesquisa de Satisfação'
    
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
        
        Args:
            obj: Instância de GlpiCategory
            
        Returns:
            str: Nome da categoria do nível 5 ou '-' se não houver
        """
        path = get_category_path(obj)
        return path[4] if len(path) > 4 else '-'
    level_5.short_description = 'Nível 5'

    def level_6(self, obj):
        """
        Retorna o nome da categoria do nível 6 da hierarquia.
        
        Args:
            obj: Instância de GlpiCategory
            
        Returns:
            str: Nome da categoria do nível 6 ou '-' se não houver
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
    list_display = ('id', 'suggested_path', 'ticket_link', 'source', 'status', 'created_at', 'reviewed_at')
    list_filter = ('status', 'source', 'created_at', 'reviewed_at')
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
    actions = ['approve_suggestions', 'reject_suggestions', 'reset_to_pending']
    
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
        """
        Exibe link para o ticket relacionado.
        
        Args:
            obj: Instância de CategorySuggestion
            
        Returns:
            str: Link HTML para o ticket, 'Preview' se for preview, ou '-' se não houver
        """
        if obj.ticket:
            return mark_safe(f'<a href="/admin/core/ticket/{obj.ticket.id}/change/">Ticket #{obj.ticket.id}</a>')
        elif obj.source == 'preview':
            return 'Preview'
        return '-'
    ticket_link.short_description = 'Ticket'
    
    def ticket_content_display(self, obj):
        """
        Exibe conteúdo do ticket formatado.
        
        Args:
            obj: Instância de CategorySuggestion
            
        Returns:
            str: Conteúdo formatado em HTML ou '-' se vazio
        """
        if not obj.ticket_content:
            return "-"
        return mark_safe(obj.ticket_content.replace('\n', '<br>'))
    ticket_content_display.short_description = 'Conteúdo do Ticket'
    
    def approve_suggestions(self, request, queryset):
        """
        Aprova sugestões selecionadas.
        
        Args:
            request: Requisição HTTP
            queryset: QuerySet de sugestões selecionadas
        """
        count = 0
        for suggestion in queryset.filter(status='pending'):  # Valor do choice CATEGORY_SUGGESTION_STATUS_CHOICES
            suggestion.status = 'approved'  # Valor do choice CATEGORY_SUGGESTION_STATUS_CHOICES
            suggestion.reviewed_at = timezone.now()
            suggestion.reviewed_by = request.user.username
            suggestion.save()
            count += 1
        self.message_user(request, f'{count} sugestão(ões) aprovada(s).')
    approve_suggestions.short_description = 'Aprovar sugestões selecionadas'
    
    def reject_suggestions(self, request, queryset):
        """
        Rejeita sugestões selecionadas.
        
        Args:
            request: Requisição HTTP
            queryset: QuerySet de sugestões selecionadas
        """
        count = 0
        for suggestion in queryset.filter(status='pending'):  # Valor do choice CATEGORY_SUGGESTION_STATUS_CHOICES
            suggestion.status = 'rejected'  # Valor do choice CATEGORY_SUGGESTION_STATUS_CHOICES
            suggestion.reviewed_at = timezone.now()
            suggestion.reviewed_by = request.user.username
            suggestion.save()
            count += 1
        self.message_user(request, f'{count} sugestão(ões) rejeitada(s).')
    reject_suggestions.short_description = 'Rejeitar sugestões selecionadas'
    
    def reset_to_pending(self, request, queryset):
        """
        Reverte sugestões aprovadas/rejeitadas para pendente.
        
        Limpa os campos de revisão (reviewed_at, reviewed_by) e altera
        o status para 'pending', permitindo nova revisão.
        
        Args:
            request: Requisição HTTP
            queryset: QuerySet de sugestões selecionadas
        """
        count = 0
        for suggestion in queryset.exclude(status='pending'):  # Valor do choice CATEGORY_SUGGESTION_STATUS_CHOICES
            suggestion.status = 'pending'  # Valor do choice CATEGORY_SUGGESTION_STATUS_CHOICES
            suggestion.reviewed_at = None
            suggestion.reviewed_by = None
            suggestion.save()
            count += 1
        self.message_user(request, f'{count} sugestão(ões) revertida(s) para pendente.')
    reset_to_pending.short_description = 'Reverter para pendente'

@admin.register(SatisfactionSurvey)
class SatisfactionSurveyAdmin(admin.ModelAdmin):
    """
    Configuração do admin para pesquisas de satisfação.
    
    Exibe pesquisas respondidas pelos usuários sobre o atendimento recebido.
    """
    list_display = ('id', 'ticket_link', 'rating_display', 'comment_preview', 'token_status', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('ticket__id', 'comment')
    readonly_fields = ('ticket', 'rating', 'comment_display', 'token_display', 'token_expires_at', 'created_at')
    actions = ['reset_token_action']
    
    fieldsets = (
        ('Pesquisa', {
            'fields': (
                'ticket',
                'rating',
                'comment_display'
            )
        }),
        ('Segurança (Token)', {
            'fields': ('token_display', 'token_expires_at'),
            'classes': ('collapse',),
            'description': 'Token de segurança para validar a pesquisa. Use a ação "Resetar token" para permitir nova resposta.'
        }),
        ('Metadados', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def ticket_link(self, obj):
        """
        Exibe link para o ticket relacionado.
        
        Args:
            obj: Instância de SatisfactionSurvey
            
        Returns:
            str: Link HTML para o ticket
        """
        return mark_safe(f'<a href="/admin/core/ticket/{obj.ticket.id}/change/">{obj.ticket.id}</a>')
    ticket_link.short_description = 'Ticket'
    
    def rating_display(self, obj):
        """
        Exibe nota formatada.
        
        Args:
            obj: Instância de SatisfactionSurvey
            
        Returns:
            str: Nota formatada como "X/5 - [Label]"
        """
        return f"{obj.rating}/5 - {obj.get_rating_display()}"
    rating_display.short_description = 'Nota'
    
    def comment_preview(self, obj):
        """
        Exibe preview do comentário (primeiros 50 caracteres).
        
        Args:
            obj: Instância de SatisfactionSurvey
            
        Returns:
            str: Preview do comentário ou '-' se não houver
        """
        if obj.comment:
            preview = obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
            return preview
        return "-"
    comment_preview.short_description = 'Comentário'
    
    def comment_display(self, obj):
        """
        Exibe comentário completo formatado.
        
        Args:
            obj: Instância de SatisfactionSurvey
            
        Returns:
            str: Comentário formatado em HTML ou '-' se vazio
        """
        if not obj.comment:
            return "-"
        return mark_safe(obj.comment.replace('\n', '<br>'))
    comment_display.short_description = 'Comentário Completo'
    
    def token_display(self, obj):
        """
        Exibe token de segurança (primeiros e últimos caracteres).
        
        Args:
            obj: Instância de SatisfactionSurvey
            
        Returns:
            str: Token formatado ou 'Não gerado' se não houver
        """
        if not obj.token:
            return "-"
        # Mostra primeiros 8 e últimos 8 caracteres
        return f"{obj.token[:8]}...{obj.token[-8:]}"
    token_display.short_description = 'Token'
    
    def token_status(self, obj):
        """
        Exibe status do token (ativo/expirado/sem token).
        
        Args:
            obj: Instância de SatisfactionSurvey
            
        Returns:
            str: Status do token formatado
        """
        if not obj.token:
            return mark_safe('<span style="color: #999;">Sem token</span>')
        
        if obj.token_expires_at and timezone.now() > obj.token_expires_at:
            return mark_safe('<span style="color: #dc3545;">Expirado</span>')
        
        return mark_safe('<span style="color: #28a745;">Ativo</span>')
    token_status.short_description = 'Status Token'
    
    def reset_token_action(self, request, queryset):
        """
        Ação para resetar token de pesquisas selecionadas.
        
        Permite que o usuário responda a pesquisa novamente.
        
        Args:
            request: Requisição HTTP
            queryset: QuerySet de pesquisas selecionadas
        """
        count = 0
        for survey in queryset:
            survey.reset_token()
            count += 1
        
        self.message_user(
            request,
            f'{count} token(s) resetado(s) com sucesso. O usuário poderá responder a pesquisa novamente.'
        )
    reset_token_action.short_description = 'Resetar token (permitir nova resposta)'


@admin.register(KnowledgeBaseArticle)
class KnowledgeBaseArticleAdmin(admin.ModelAdmin):
    """
    Configuração do admin para artigos de Base de Conhecimento.
    
    Exibe artigos gerados pela IA, permitindo revisão e reutilização.
    """
    list_display = ('id', 'article_type', 'category_short', 'source', 'created_at')
    list_filter = ('article_type', 'source', 'created_at')
    search_fields = ('category', 'context', 'content')
    readonly_fields = (
        'article_type',
        'category',
        'context',
        'content_display',
        'content_html_display',
        'content_html_raw',
        'source',
        'created_at',
        'updated_at'
    )
    
    fieldsets = (
        ('Artigo', {
            'fields': (
                'article_type',
                'category',
                'source',
            )
        }),
        ('Conteúdo', {
            'fields': (
                'context',
                'content_display',
                'content_html_display',
                'content_html_raw',
            )
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def category_short(self, obj):
        """Exibe categoria truncada para a listagem."""
        if len(obj.category) > 50:
            return obj.category[:50] + '...'
        return obj.category
    category_short.short_description = 'Categoria'
    
    def content_display(self, obj):
        """Exibe conteúdo Markdown formatado."""
        if not obj.content:
            return "-"
        return mark_safe(
            f'<pre style="white-space: pre-wrap; max-height: 400px; overflow-y: auto; '
            f'padding: 1rem; border: 1px solid rgba(128, 128, 128, 0.3); '
            f'border-radius: 4px; margin: 0; background: transparent;">{obj.content}</pre>'
        )
    content_display.short_description = 'Conteúdo (Markdown)'
    
    def content_html_display(self, obj):
        """Exibe conteúdo HTML formatado."""
        if not obj.content_html:
            return "-"
        return mark_safe(f'<div style="max-height: 400px; overflow-y: auto;">{obj.content_html}</div>')
    content_html_display.short_description = 'Conteúdo (HTML)'
    
    def content_html_raw(self, obj):
        """Exibe conteúdo HTML bruto (código-fonte) para copiar."""
        if not obj.content_html:
            return "-"
        from django.utils.html import escape
        escaped_html = escape(obj.content_html)
        return mark_safe(
            f'<pre style="white-space: pre-wrap; max-height: 400px; overflow-y: auto; '
            f'padding: 1rem; border: 1px solid rgba(128, 128, 128, 0.3); '
            f'border-radius: 4px; font-family: monospace; font-size: 0.9em; '
            f'margin: 0; background: transparent;">{escaped_html}</pre>'
        )
    content_html_raw.short_description = 'HTML Bruto (Código-Fonte)'
