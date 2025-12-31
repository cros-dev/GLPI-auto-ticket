"""
Configuração do admin para o app accounts (SSPR).

Registra os models relacionados a reset de senha e integração com Zoho.
"""
from django.contrib import admin
from django.contrib import messages
from django.utils.html import mark_safe
from django.utils import timezone
from datetime import timedelta
from .models import ZohoToken, PasswordResetRequest, OtpToken
from .constants import MAX_RESET_REQUESTS_PER_HOUR


@admin.register(ZohoToken)
class ZohoTokenAdmin(admin.ModelAdmin):
    """
    Configuração do admin para tokens Zoho.
    
    Exibe tokens OAuth do Zoho, permitindo visualizar e gerenciar
    refresh tokens e access tokens.
    """
    list_display = ('id', 'refresh_token_display', 'access_token_status', 'scope', 'api_domain', 'expires_at', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('refresh_token', 'scope')
    readonly_fields = (
        'refresh_token',
        'access_token_display',
        'expires_at',
        'scope',
        'api_domain',
        'created_at',
        'updated_at'
    )
    
    fieldsets = (
        ('Tokens OAuth', {
            'fields': (
                'refresh_token',
                'access_token_display',
                'expires_at',
            )
        }),
        ('Configuração', {
            'fields': (
                'scope',
                'api_domain',
            )
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def refresh_token_display(self, obj):
        """Exibe refresh token truncado."""
        if not obj.refresh_token:
            return "-"
        return f"{obj.refresh_token[:20]}...{obj.refresh_token[-10:]}"
    refresh_token_display.short_description = 'Refresh Token'
    
    def access_token_display(self, obj):
        """Exibe access token truncado."""
        if not obj.access_token:
            return "-"
        return f"{obj.access_token[:20]}...{obj.access_token[-10:]}"
    access_token_display.short_description = 'Access Token'
    
    def access_token_status(self, obj):
        """Exibe status do access token (válido/expirado/sem token)."""
        if not obj.access_token:
            return mark_safe('<span style="color: #999;">Sem token</span>')
        
        if obj.is_access_token_valid():
            return mark_safe('<span style="color: #28a745;">Válido</span>')
        
        return mark_safe('<span style="color: #dc3545;">Expirado</span>')
    access_token_status.short_description = 'Status Access Token'


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    """
    Configuração do admin para solicitações de reset de senha.
    
    Exibe solicitações de reset, permitindo acompanhar o processo
    e identificar problemas. Permite ações administrativas para
    resetar limites e intervir em casos bloqueados.
    """
    list_display = ('id', 'token_display', 'identifier', 'system', 'status', 'created_at', 'expires_at', 'completed_at', 'recent_requests_count')
    list_filter = ('status', 'system', 'created_at', 'expires_at')
    search_fields = ('token', 'identifier')
    actions = ['reset_rate_limit', 'unlock_user', 'expire_old_requests']
    readonly_fields = (
        'token',
        'identifier',
        'system',
        'status',
        'created_at',
        'expires_at',
        'completed_at',
        'otp_tokens_display',
        'recent_requests_info'
    )
    
    fieldsets = (
        ('Solicitação', {
            'fields': (
                'token',
                'identifier',
                'system',
                'status',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'expires_at',
                'completed_at',
            )
        }),
        ('Informações de Limite', {
            'fields': ('recent_requests_info',),
            'description': 'Informações sobre solicitações recentes deste usuário (última hora).'
        }),
        ('Tokens OTP Relacionados', {
            'fields': ('otp_tokens_display',),
            'classes': ('collapse',)
        }),
    )
    
    def token_display(self, obj):
        """Exibe token truncado."""
        if not obj.token:
            return "-"
        return f"{obj.token[:10]}...{obj.token[-10:]}"
    token_display.short_description = 'Token'
    
    def otp_tokens_display(self, obj):
        """Exibe lista de tokens OTP relacionados."""
        otp_tokens = obj.otp_tokens.all()
        if not otp_tokens.exists():
            return "-"
        
        html = "<ul>"
        for otp in otp_tokens:
            status_color = {
                'pending': '#ffc107',
                'validated': '#28a745',
                'expired': '#dc3545',
                'exceeded_attempts': '#dc3545'
            }.get(otp.status, '#999')
            
            html += f'<li>'
            html += f'<strong>Código:</strong> {otp.code} | '
            html += f'<strong>Método:</strong> {otp.method} | '
            html += f'<strong>Status:</strong> <span style="color: {status_color};">{otp.get_status_display()}</span> | '
            html += f'<strong>Tentativas:</strong> {otp.attempts} | '
            html += f'<strong>Criado:</strong> {otp.created_at.strftime("%d/%m/%Y %H:%M")}'
            html += f'</li>'
        html += "</ul>"
        
        return mark_safe(html)
    otp_tokens_display.short_description = 'Tokens OTP'
    
    def recent_requests_count(self, obj):
        """Exibe contagem de solicitações recentes (última hora) para este usuário."""
        one_hour_ago = timezone.now() - timedelta(hours=1)
        count = PasswordResetRequest.objects.filter(
            identifier=obj.identifier,
            created_at__gte=one_hour_ago
        ).count()
        
        if count >= MAX_RESET_REQUESTS_PER_HOUR:
            return mark_safe(f'<span style="color: #dc3545; font-weight: bold;">{count}/{MAX_RESET_REQUESTS_PER_HOUR} (BLOQUEADO)</span>')
        return f'{count}/{MAX_RESET_REQUESTS_PER_HOUR}'
    recent_requests_count.short_description = 'Solicitações (1h)'
    
    def recent_requests_info(self, obj):
        """Exibe informações detalhadas sobre solicitações recentes."""
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent = PasswordResetRequest.objects.filter(
            identifier=obj.identifier,
            created_at__gte=one_hour_ago
        ).order_by('-created_at')
        
        count = recent.count()
        limit = MAX_RESET_REQUESTS_PER_HOUR
        
        html = f'<p><strong>Solicitações na última hora:</strong> {count}/{limit}</p>'
        
        if count >= limit:
            html += '<p style="color: #dc3545; font-weight: bold;">⚠️ Usuário bloqueado (limite atingido)</p>'
            html += '<p><em>Use a ação "🔓 Liberar usuário" para remover todas as solicitações e liberar imediatamente.</em></p>'
        
        if recent.exists():
            html += '<ul style="margin-top: 10px;">'
            for req in recent[:5]:  # Mostra apenas as 5 mais recentes
                status_color = {
                    'pending': '#ffc107',
                    'otp_validated': '#17a2b8',
                    'completed': '#28a745',
                    'expired': '#6c757d',
                    'failed': '#dc3545'
                }.get(req.status, '#999')
                
                html += f'<li>'
                html += f'<strong>#{req.id}</strong> - '
                html += f'<span style="color: {status_color};">{req.get_status_display()}</span> - '
                html += f'{req.created_at.strftime("%d/%m/%Y %H:%M:%S")}'
                html += f'</li>'
            html += '</ul>'
        
        return mark_safe(html)
    recent_requests_info.short_description = 'Informações de Limite'
    
    @admin.action(description='Resetar limite de tentativas (apagar solicitações antigas)')
    def reset_rate_limit(self, request, queryset):
        """
        Action para resetar limite de tentativas.
        
        Apaga solicitações antigas (mais de 1 hora) dos usuários selecionados,
        permitindo que façam novas solicitações.
        """
        one_hour_ago = timezone.now() - timedelta(hours=1)
        identifiers = queryset.values_list('identifier', flat=True).distinct()
        
        deleted_count = 0
        for identifier in identifiers:
            deleted = PasswordResetRequest.objects.filter(
                identifier=identifier,
                created_at__lt=one_hour_ago
            ).delete()[0]
            deleted_count += deleted
        
        self.message_user(
            request,
            f'Limite resetado para {len(identifiers)} usuário(s). {deleted_count} solicitação(ões) antiga(s) removida(s).',
            messages.SUCCESS
        )
    
    @admin.action(description='🔓 Liberar usuário (deletar TODAS as solicitações recentes)')
    def unlock_user(self, request, queryset):
        """
        Action para liberar usuário bloqueado.
        
        Deleta TODAS as solicitações dos usuários selecionados (incluindo recentes),
        permitindo que façam novas solicitações imediatamente.
        
        ⚠️ ATENÇÃO: Esta ação remove todas as solicitações, mesmo as recentes.
        Use quando o usuário está bloqueado e precisa ser liberado imediatamente.
        """
        identifiers = queryset.values_list('identifier', flat=True).distinct()
        
        deleted_count = 0
        for identifier in identifiers:
            deleted = PasswordResetRequest.objects.filter(
                identifier=identifier
            ).delete()[0]
            deleted_count += deleted
        
        self.message_user(
            request,
            f'✅ {len(identifiers)} usuário(s) liberado(s). {deleted_count} solicitação(ões) removida(s) (incluindo recentes).',
            messages.SUCCESS
        )
    
    @admin.action(description='Expirar solicitações antigas selecionadas')
    def expire_old_requests(self, request, queryset):
        """
        Action para expirar solicitações antigas manualmente.
        
        Marca solicitações selecionadas como expiradas.
        """
        updated = queryset.filter(status__in=['pending', 'otp_validated']).update(
            status='expired'
        )
        
        self.message_user(
            request,
            f'{updated} solicitação(ões) marcada(s) como expirada(s).',
            messages.SUCCESS
        )


@admin.register(OtpToken)
class OtpTokenAdmin(admin.ModelAdmin):
    """
    Configuração do admin para tokens OTP.
    
    Exibe tokens OTP gerados para validação de reset de senha.
    Permite ações administrativas para resetar tentativas.
    """
    list_display = ('id', 'reset_request_link', 'code', 'method', 'status', 'attempts', 'attempts_display', 'created_at', 'expires_at')
    list_filter = ('status', 'method', 'created_at', 'expires_at')
    search_fields = ('code', 'reset_request__token', 'reset_request__identifier')
    actions = ['reset_attempts']
    readonly_fields = (
        'reset_request',
        'code',
        'method',
        'status',
        'attempts',
        'created_at',
        'expires_at',
        'status_display'
    )
    
    fieldsets = (
        ('Token OTP', {
            'fields': (
                'reset_request',
                'code',
                'method',
                'status',
                'status_display',
                'attempts',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'expires_at',
            )
        }),
    )
    
    def reset_request_link(self, obj):
        """Exibe link para a solicitação de reset relacionada."""
        if not obj.reset_request:
            return "-"
        url = f"/admin/accounts/passwordresetrequest/{obj.reset_request.id}/change/"
        return mark_safe(f'<a href="{url}">#{obj.reset_request.id}</a>')
    reset_request_link.short_description = 'Solicitação'
    
    def status_display(self, obj):
        """Exibe status formatado com cor."""
        status_colors = {
            'pending': '#ffc107',
            'validated': '#28a745',
            'expired': '#dc3545',
            'exceeded_attempts': '#dc3545'
        }
        color = status_colors.get(obj.status, '#999')
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>')
    status_display.short_description = 'Status (Visual)'
    
    def attempts_display(self, obj):
        """Exibe tentativas com indicação visual se excedeu limite."""
        from .constants import MAX_OTP_ATTEMPTS
        if obj.attempts >= MAX_OTP_ATTEMPTS:
            return mark_safe(f'<span style="color: #dc3545; font-weight: bold;">{obj.attempts}/{MAX_OTP_ATTEMPTS} (BLOQUEADO)</span>')
        return f'{obj.attempts}/{MAX_OTP_ATTEMPTS}'
    attempts_display.short_description = 'Tentativas'
    
    @admin.action(description='Resetar tentativas de OTP (permitir novas tentativas)')
    def reset_attempts(self, request, queryset):
        """
        Action para resetar tentativas de OTP.
        
        Reseta o contador de tentativas e o status para 'pending',
        permitindo que o usuário tente validar o OTP novamente.
        """
        from .constants import MAX_OTP_ATTEMPTS
        
        updated = queryset.filter(status='exceeded_attempts').update(
            attempts=0,
            status='pending'
        )
        
        # Também reseta tentativas de tokens que ainda estão pendentes mas com muitas tentativas
        queryset.filter(status='pending', attempts__gte=MAX_OTP_ATTEMPTS).update(
            attempts=0
        )
        
        self.message_user(
            request,
            f'{updated} token(s) OTP resetado(s). Usuários podem tentar validar novamente.',
            messages.SUCCESS
        )
