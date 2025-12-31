"""
Serializers para validação e serialização de dados da API SSPR.

Este módulo contém todos os serializers usados para:
- Validação de dados de entrada
- Serialização de dados de saída
- Transformação entre modelos Django e JSON
"""
from rest_framework import serializers
from .models import PasswordResetRequest
from .constants import SYSTEM_CHOICES


# =========================================================
# 1. SOLICITAÇÃO DE RESET DE SENHA
# =========================================================

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer para solicitar reset de senha.
    
    Valida os dados de entrada para criar uma nova solicitação
    de reset de senha.
    """
    identifier = serializers.EmailField(
        help_text="Email do usuário no sistema (Zoho ou AD)"
    )
    system = serializers.ChoiceField(
        choices=[choice[0] for choice in SYSTEM_CHOICES],
        default='zoho',
        help_text="Sistema onde a senha será resetada ('zoho', 'ad', ou 'both')"
    )
    
    def validate_identifier(self, value):
        """Valida formato do email."""
        if not value or not value.strip():
            raise serializers.ValidationError("Email não pode ser vazio.")
        return value.strip().lower()
    
    def validate_system(self, value):
        """Valida sistema escolhido."""
        valid_systems = [choice[0] for choice in SYSTEM_CHOICES]
        if value not in valid_systems:
            raise serializers.ValidationError(
                f"Sistema inválido. Opções: {', '.join(valid_systems)}"
            )
        return value


class PasswordResetRequestResponseSerializer(serializers.ModelSerializer):
    """
    Serializer para resposta de solicitação de reset de senha.
    
    Retorna informações sobre a solicitação criada, incluindo
    o token para validação de OTP.
    """
    
    class Meta:
        model = PasswordResetRequest
        fields = [
            'token',
            'identifier',
            'system',
            'status',
            'created_at',
            'expires_at'
        ]
        read_only_fields = fields


# =========================================================
# 2. VALIDAÇÃO DE OTP
# =========================================================

class OtpValidationSerializer(serializers.Serializer):
    """
    Serializer para validar código OTP.
    
    Valida o código OTP informado pelo usuário para prosseguir
    com o reset de senha.
    """
    token = serializers.CharField(
        help_text="Token da solicitação de reset de senha"
    )
    otp_code = serializers.CharField(
        max_length=6,
        min_length=6,
        help_text="Código OTP de 6 dígitos recebido via SMS"
    )
    
    def validate_token(self, value):
        """Valida formato do token."""
        if not value or not value.strip():
            raise serializers.ValidationError("Token não pode ser vazio.")
        return value.strip()
    
    def validate_otp_code(self, value):
        """Valida formato do código OTP."""
        if not value or not value.strip():
            raise serializers.ValidationError("Código OTP não pode ser vazio.")
        
        code = value.strip()
        if not code.isdigit():
            raise serializers.ValidationError("Código OTP deve conter apenas dígitos.")
        
        if len(code) != 6:
            raise serializers.ValidationError("Código OTP deve ter 6 dígitos.")
        
        return code


class OtpValidationResponseSerializer(serializers.Serializer):
    """
    Serializer para resposta de validação de OTP.
    
    Retorna status da validação e informações sobre a solicitação.
    """
    valid = serializers.BooleanField(
        help_text="True se OTP foi validado com sucesso"
    )
    token = serializers.CharField(
        help_text="Token da solicitação de reset"
    )
    message = serializers.CharField(
        help_text="Mensagem sobre o status da validação"
    )


# =========================================================
# 3. CONFIRMAÇÃO DE RESET DE SENHA
# =========================================================

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer para confirmar reset de senha.
    
    Valida os dados para executar o reset de senha após
    validação do OTP.
    """
    token = serializers.CharField(
        help_text="Token da solicitação de reset de senha (após OTP validado)"
    )
    new_password = serializers.CharField(
        min_length=8,
        write_only=True,
        help_text="Nova senha (mínimo 8 caracteres)"
    )
    
    def validate_token(self, value):
        """Valida formato do token."""
        if not value or not value.strip():
            raise serializers.ValidationError("Token não pode ser vazio.")
        return value.strip()
    
    def validate_new_password(self, value):
        """Valida força da senha."""
        if not value:
            raise serializers.ValidationError("Senha não pode ser vazia.")
        
        if len(value) < 8:
            raise serializers.ValidationError("Senha deve ter no mínimo 8 caracteres.")
        
        # Verificar se tem pelo menos uma letra maiúscula, minúscula e número
        has_upper = any(c.isupper() for c in value)
        has_lower = any(c.islower() for c in value)
        has_digit = any(c.isdigit() for c in value)
        
        if not (has_upper and has_lower and has_digit):
            raise serializers.ValidationError(
                "Senha deve conter pelo menos uma letra maiúscula, "
                "uma minúscula e um número."
            )
        
        return value


class PasswordResetConfirmResponseSerializer(serializers.Serializer):
    """
    Serializer para resposta de confirmação de reset de senha.
    
    Retorna status do reset e informações sobre a conclusão.
    """
    success = serializers.BooleanField(
        help_text="True se senha foi resetada com sucesso"
    )
    message = serializers.CharField(
        help_text="Mensagem sobre o resultado do reset"
    )
    identifier = serializers.CharField(
        help_text="Email do usuário que teve a senha resetada"
    )

