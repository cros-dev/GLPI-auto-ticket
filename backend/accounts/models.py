"""
Modelos de dados para o sistema de SSPR (Self-Service Password Reset).

Este módulo contém os modelos principais:
- ZohoToken: Armazena tokens OAuth do Zoho (refresh_token, access_token)
- SystemAccount: Vincula usuários a contas externas (Zoho, AD)
- PasswordResetRequest: Solicitações de reset de senha
- OtpToken: Tokens OTP para validação (SMS ou email)
"""
import secrets
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from .constants import (
    SYSTEM_CHOICES, 
    SYSTEM_ACCOUNT_CHOICES, 
    OTP_METHOD_CHOICES,
    OTP_STATUS_CHOICES,
    RESET_REQUEST_STATUS_CHOICES
)

User = get_user_model()


class ZohoToken(models.Model):
    """
    Armazena tokens OAuth do Zoho para autenticação automática.
    
    O refresh_token é gerado uma única vez e usado para renovar
    access_tokens automaticamente quando expiram.
    """
    
    # Refresh token (não expira, gerado uma vez)
    refresh_token = models.CharField(
        max_length=500,
        unique=True,
        help_text="Refresh token do Zoho (não expira, gerado uma vez)"
    )
    
    # Access token (expira em ~1 hora)
    access_token = models.TextField(
        null=True,
        blank=True,
        help_text="Access token atual do Zoho (expira em ~1 hora)"
    )
    
    # Data de expiração do access token
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data/hora de expiração do access token"
    )
    
    # Scopes autorizados
    scope = models.CharField(
        max_length=500,
        blank=True,
        help_text="Scopes autorizados no Zoho"
    )
    
    # API domain do Zoho
    api_domain = models.URLField(
        default="https://www.zohoapis.com",
        help_text="API domain do Zoho"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Token Zoho'
        verbose_name_plural = 'Tokens Zoho'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Zoho Token (expira: {self.expires_at})"
    
    def is_access_token_valid(self) -> bool:
        """
        Verifica se o access token ainda é válido.
        
        Returns:
            bool: True se válido, False se expirado ou não existe
        """
        if not self.access_token or not self.expires_at:
            return False
        
        return timezone.now() < self.expires_at
    
    def needs_refresh(self) -> bool:
        """
        Verifica se o access token precisa ser renovado.
        
        Returns:
            bool: True se precisa renovar, False caso contrário
        """
        return not self.is_access_token_valid()


class SystemAccount(models.Model):
    """
    Vincula usuários do Django a contas em sistemas externos (Zoho, AD).
    
    Permite rastrear qual email Zoho ou username AD pertence a cada usuário.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='system_accounts',
        help_text="Usuário do Django vinculado"
    )
    
    system = models.CharField(
        max_length=20,
        choices=SYSTEM_ACCOUNT_CHOICES,
        help_text="Sistema externo (Zoho ou AD)"
    )
    
    # Para Zoho: email da conta
    zoho_email = models.EmailField(
        null=True,
        blank=True,
        help_text="Email da conta Zoho"
    )
    
    # Para AD: username
    ad_username = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Username no Active Directory"
    )
    
    # Número de telefone para SMS OTP (hash ou criptografado)
    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Número de telefone para SMS OTP (formato internacional)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Conta de Sistema'
        verbose_name_plural = 'Contas de Sistema'
        unique_together = [['user', 'system']]
        ordering = ['user', 'system']
    
    def __str__(self):
        if self.system == 'zoho' and self.zoho_email:
            return f"{self.user.username} - Zoho: {self.zoho_email}"
        elif self.system == 'ad' and self.ad_username:
            return f"{self.user.username} - AD: {self.ad_username}"
        return f"{self.user.username} - {self.system}"


class PasswordResetRequest(models.Model):
    """
    Solicitação de reset de senha.
    
    Armazena o estado de cada solicitação de reset, incluindo
    sistema alvo, status e tokens relacionados.
    """
    
    # Token único para identificar a solicitação
    token = models.CharField(
        max_length=64,
        unique=True,
        help_text="Token único da solicitação"
    )
    
    # Usuário que solicitou (pode ser None se identificado apenas por email/telefone)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='password_reset_requests',
        help_text="Usuário que solicitou (se identificado)"
    )
    
    # Sistema alvo do reset
    system = models.CharField(
        max_length=20,
        choices=SYSTEM_CHOICES,
        help_text="Sistema onde a senha será resetada"
    )
    
    # Email ou identificador usado na solicitação
    identifier = models.CharField(
        max_length=255,
        help_text="Email ou identificador usado na solicitação"
    )
    
    # Status da solicitação
    status = models.CharField(
        max_length=20,
        choices=RESET_REQUEST_STATUS_CHOICES,
        default='pending',
        help_text="Status atual da solicitação"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Data/hora de expiração da solicitação (padrão: 1 hora)"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data/hora de conclusão do reset"
    )
    
    class Meta:
        verbose_name = 'Solicitação de Reset de Senha'
        verbose_name_plural = 'Solicitações de Reset de Senha'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reset {self.system} - {self.identifier} ({self.status})"
    
    def generate_token(self):
        """Gera um token único seguro para a solicitação."""
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        return self.token
    
    def is_expired(self) -> bool:
        """
        Verifica se a solicitação expirou.
        
        Returns:
            bool: True se expirada, False caso contrário
        """
        return timezone.now() > self.expires_at
    
    def save(self, *args, **kwargs):
        """Gera token e define expiração se não existirem."""
        if not self.token:
            self.generate_token()
        if not self.expires_at:
            # Expira em 1 hora
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)


class OtpToken(models.Model):
    """
    Token OTP (One-Time Password) para validação de reset de senha.
    
    Pode ser enviado via SMS ou email. Expira rapidamente e tem
    limite de tentativas.
    """
    
    # Relacionamento com solicitação
    reset_request = models.ForeignKey(
        PasswordResetRequest,
        on_delete=models.CASCADE,
        related_name='otp_tokens',
        help_text="Solicitação de reset relacionada"
    )
    
    # Código OTP (6 dígitos)
    code = models.CharField(
        max_length=6,
        help_text="Código OTP de 6 dígitos"
    )
    
    # Método de envio
    method = models.CharField(
        max_length=10,
        choices=OTP_METHOD_CHOICES,
        help_text="Método usado para enviar OTP (SMS ou Email)"
    )
    
    # Status do token
    status = models.CharField(
        max_length=20,
        choices=OTP_STATUS_CHOICES,
        default='pending',
        help_text="Status atual do token OTP"
    )
    
    # Contador de tentativas
    attempts = models.IntegerField(
        default=0,
        help_text="Número de tentativas de validação"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Data/hora de expiração do OTP (padrão: 10 minutos)"
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data/hora de validação do OTP"
    )
    
    class Meta:
        verbose_name = 'Token OTP'
        verbose_name_plural = 'Tokens OTP'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP {self.method} - {self.reset_request.identifier} ({self.status})"
    
    def generate_code(self) -> str:
        """
        Gera um código OTP de 6 dígitos.
        
        Returns:
            str: Código OTP de 6 dígitos
        """
        self.code = f"{secrets.randbelow(1000000):06d}"
        return self.code
    
    def is_expired(self) -> bool:
        """
        Verifica se o OTP expirou.
        
        Returns:
            bool: True se expirado, False caso contrário
        """
        return timezone.now() > self.expires_at
    
    def has_exceeded_attempts(self) -> bool:
        """
        Verifica se excedeu o limite de tentativas (máximo 3).
        
        Returns:
            bool: True se excedeu, False caso contrário
        """
        return self.attempts >= 3
    
    def increment_attempts(self):
        """Incrementa o contador de tentativas."""
        self.attempts += 1
        if self.has_exceeded_attempts():
            self.status = 'exceeded_attempts'
        self.save(update_fields=['attempts', 'status'])
    
    def save(self, *args, **kwargs):
        """Gera código e define expiração se não existirem."""
        if not self.code:
            self.generate_code()
        if not self.expires_at:
            # Expira em 10 minutos
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
