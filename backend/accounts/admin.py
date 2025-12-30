"""
Configuração do admin para o app accounts (SSPR).

Registra os models relacionados a reset de senha e integração com Zoho/AD.
"""
from django.contrib import admin
from django.utils.html import mark_safe
from django.utils import timezone
from .models import ZohoToken, SystemAccount, PasswordResetRequest, OtpToken
from .constants import (
    RESET_REQUEST_STATUS_CHOICES,
    OTP_STATUS_CHOICES,
    SYSTEM_CHOICES
)


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


@admin.register(SystemAccount)
class SystemAccountAdmin(admin.ModelAdmin):
    """
    Configuração do admin para contas de sistema.
    
    Exibe vínculos entre usuários Django e contas externas (Zoho, AD).
    """
    list_display = ('id', 'user', 'system', 'zoho_email', 'ad_username', 'phone_number_display', 'created_at', 'updated_at')
    list_filter = ('system', 'created_at')
    search_fields = ('user__username', 'zoho_email', 'ad_username', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Vínculo', {
            'fields': (
                'user',
                'system',
            )
        }),
        ('Credenciais Zoho', {
            'fields': ('zoho_email',),
            'description': 'Email da conta Zoho vinculada ao usuário.'
        }),
        ('Credenciais Active Directory', {
            'fields': ('ad_username',),
            'description': 'Username no Active Directory vinculado ao usuário.'
        }),
        ('Contato', {
            'fields': ('phone_number',),
            'description': 'Número de telefone para SMS OTP (formato internacional).'
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def phone_number_display(self, obj):
        """Exibe número de telefone mascarado."""
        if not obj.phone_number:
            return "-"
        # Mostra apenas últimos 4 dígitos
        if len(obj.phone_number) > 4:
            return f"****{obj.phone_number[-4:]}"
        return "****"
    phone_number_display.short_description = 'Telefone'


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    """
    Configuração do admin para solicitações de reset de senha.
    
    Exibe solicitações de reset, permitindo acompanhar o processo
    e identificar problemas.
    """
    list_display = ('id', 'token_display', 'user', 'identifier', 'system', 'status', 'created_at', 'expires_at', 'completed_at')
    list_filter = ('status', 'system', 'created_at', 'expires_at')
    search_fields = ('token', 'identifier', 'user__username')
    readonly_fields = (
        'token',
        'user',
        'identifier',
        'system',
        'status',
        'created_at',
        'expires_at',
        'completed_at',
        'otp_tokens_display'
    )
    
    fieldsets = (
        ('Solicitação', {
            'fields': (
                'token',
                'user',
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
            html += f'<strong>Criado:</strong> {otp.created_at.strftime("%d/%m/%Y %H:%M")}'
            html += f'</li>'
        html += "</ul>"
        
        return mark_safe(html)
    otp_tokens_display.short_description = 'Tokens OTP'


@admin.register(OtpToken)
class OtpTokenAdmin(admin.ModelAdmin):
    """
    Configuração do admin para tokens OTP.
    
    Exibe tokens OTP gerados para validação de reset de senha.
    """
    list_display = ('id', 'reset_request_link', 'code', 'method', 'status', 'attempts', 'created_at', 'expires_at')
    list_filter = ('status', 'method', 'created_at', 'expires_at')
    search_fields = ('code', 'reset_request__token', 'reset_request__identifier')
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
