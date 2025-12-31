"""
Serviços de negócio para SSPR (Self-Service Password Reset).

Este módulo contém as funções de lógica de negócio para:
- Solicitação de reset de senha
- Geração e envio de OTP
- Validação de OTP
- Confirmação e execução do reset de senha
"""
import logging
from typing import Optional, Tuple
from django.utils import timezone
from datetime import timedelta

from .models import PasswordResetRequest, OtpToken
from .clients.zoho_client import ZohoClient
from .exceptions import ZohoException, SMSException
from .clients.sms_client import SMSClient
from .constants import (
    OTP_EXPIRY_MINUTES,
    RESET_REQUEST_EXPIRY_HOURS,
    MAX_RESET_REQUESTS_PER_HOUR
)

logger = logging.getLogger(__name__)


def request_password_reset(
    identifier: str,
    system: str = 'zoho'
) -> Tuple[PasswordResetRequest, Optional[str]]:
    """
    Cria uma solicitação de reset de senha.
    
    Valida se o usuário existe no sistema especificado, obtém seus dados
    (incluindo telefone) e cria a solicitação de reset.
    
    Args:
        identifier: Email ou identificador do usuário
        system: Sistema onde a senha será resetada ('zoho', 'ad', ou 'both')
        
    Returns:
        Tuple[PasswordResetRequest, Optional[str]]: Tupla com (solicitação criada, telefone do usuário)
        
    Raises:
        ValueError: Se o usuário não for encontrado ou não tiver telefone
        ZohoException: Se houver erro ao buscar usuário no Zoho
    """
    # Verificar limite de solicitações por hora
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_requests = PasswordResetRequest.objects.filter(
        identifier=identifier,
        created_at__gte=one_hour_ago
    ).count()
    
    if recent_requests >= MAX_RESET_REQUESTS_PER_HOUR:
        raise ValueError(
            f"Limite de {MAX_RESET_REQUESTS_PER_HOUR} solicitações por hora atingido. "
            "Tente novamente mais tarde."
        )
    
    # Validar sistema
    if system not in ['zoho', 'ad', 'both']:
        raise ValueError(f"Sistema inválido: {system}")
    
    # Validar usuário no Zoho e telefone
    phone_number = None
    if system in ['zoho', 'both']:
        client = ZohoClient()
        try:
            phone_number = client.get_user_phone_by_email(identifier)
            
            if not phone_number:
                raise ValueError(
                    f"Usuário {identifier} não encontrado no Zoho ou não possui número de telefone cadastrado. "
                    "É necessário ter telefone para receber OTP via SMS."
                )
            
        except ZohoException as e:
            logger.error(f"Erro ao buscar usuário no Zoho: {e.message}")
            raise
    
    # Criar solicitação de reset
    reset_request = PasswordResetRequest.objects.create(
        identifier=identifier,
        system=system,
        status='pending',
        expires_at=timezone.now() + timedelta(hours=RESET_REQUEST_EXPIRY_HOURS)
    )
    
    logger.info(
        f"Solicitação de reset criada para {identifier} "
        f"(telefone: {phone_number[:5] + '***' if phone_number else 'N/A'})"
    )
    
    return reset_request, phone_number


def generate_otp(
    reset_request: PasswordResetRequest,
    method: str = 'sms'
) -> OtpToken:
    """
    Gera um código OTP e cria o token associado à solicitação.
    
    Args:
        reset_request: Solicitação de reset de senha
        method: Método de envio ('sms' ou 'email')
        
    Returns:
        OtpToken: Token OTP gerado
        
    Raises:
        ValueError: Se a solicitação estiver expirada ou inválida
    """
    if reset_request.is_expired():
        reset_request.status = 'expired'
        reset_request.save(update_fields=['status'])
        raise ValueError("Solicitação de reset expirada. Crie uma nova solicitação.")
    
    if reset_request.status not in ['pending', 'otp_validated']:
        raise ValueError(f"Solicitação de reset com status inválido: {reset_request.status}")
    
    # Criar token OTP
    otp_token = OtpToken.objects.create(
        reset_request=reset_request,
        method=method,
        status='pending',
        expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    )
    
    logger.info(f"OTP gerado para solicitação {reset_request.token} (método: {method})")
    
    return otp_token


def send_otp_sms(otp_token: OtpToken, phone_number: str) -> bool:
    """
    Envia código OTP via SMS usando Twilio.
    
    Args:
        otp_token: Token OTP a ser enviado
        phone_number: Número de telefone (formato internacional)
        
    Returns:
        bool: True se enviado com sucesso
        
    Raises:
        ValueError: Se configuração do Twilio estiver incompleta
        SMSException: Se houver erro ao enviar SMS
    """
    try:
        sms_client = SMSClient()
        success = sms_client.send_otp(phone_number, otp_token.code)
        
        if success:
            logger.info(
                f"OTP {otp_token.code} enviado via SMS para {phone_number[:5]}*** "
                f"(solicitação: {otp_token.reset_request.token})"
            )
        
        return success
        
    except SMSException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao enviar OTP via SMS: {str(e)}")
        raise SMSException('sms_error', f'Erro ao enviar SMS: {str(e)}') from e


def validate_otp(
    reset_request: PasswordResetRequest,
    otp_code: str
) -> bool:
    """
    Valida um código OTP.
    
    Args:
        reset_request: Solicitação de reset de senha
        otp_code: Código OTP informado pelo usuário
        
    Returns:
        bool: True se válido, False caso contrário
        
    Raises:
        ValueError: Se OTP expirado, excedeu tentativas ou solicitação inválida
    """
    if reset_request.is_expired():
        reset_request.status = 'expired'
        reset_request.save(update_fields=['status'])
        raise ValueError("Solicitação de reset expirada.")
    
    # Buscar OTP mais recente da solicitação
    otp_token = OtpToken.objects.filter(
        reset_request=reset_request,
        status='pending'
    ).order_by('-created_at').first()
    
    if not otp_token:
        raise ValueError("Nenhum OTP pendente encontrado para esta solicitação.")
    
    if otp_token.is_expired():
        otp_token.status = 'expired'
        otp_token.save(update_fields=['status'])
        raise ValueError("Código OTP expirado. Solicite um novo código.")
    
    if otp_token.has_exceeded_attempts():
        raise ValueError("Número máximo de tentativas excedido. Solicite um novo código.")
    
    # Validar código
    if otp_token.code != otp_code.strip():
        otp_token.increment_attempts()
        logger.warning(
            f"Tentativa de validação OTP falhou para solicitação {reset_request.token} "
            f"(tentativas: {otp_token.attempts})"
        )
        return False
    
    # OTP válido
    otp_token.status = 'validated'
    otp_token.validated_at = timezone.now()
    otp_token.save(update_fields=['status', 'validated_at'])
    
    reset_request.status = 'otp_validated'
    reset_request.save(update_fields=['status'])
    
    logger.info(f"OTP validado com sucesso para solicitação {reset_request.token}")
    
    return True


def confirm_password_reset(
    reset_request: PasswordResetRequest,
    new_password: str
) -> bool:
    """
    Executa o reset de senha no sistema especificado.
    
    Args:
        reset_request: Solicitação de reset de senha (deve ter OTP validado)
        new_password: Nova senha
        
    Returns:
        bool: True se resetado com sucesso
        
    Raises:
        ValueError: Se a solicitação não estiver validada ou expirada
        ZohoException: Se houver erro ao resetar senha no Zoho
    """
    if reset_request.is_expired():
        reset_request.status = 'expired'
        reset_request.save(update_fields=['status'])
        raise ValueError("Solicitação de reset expirada.")
    
    # Verificar se há um OTP validado e não expirado
    # O OTP expira em OTP_EXPIRY_MINUTES após ser criado (não após ser validado)
    validated_otp = reset_request.otp_tokens.filter(
        status='validated',
        validated_at__isnull=False,
        expires_at__gt=timezone.now()
    ).order_by('-validated_at').first()
    
    if not validated_otp:
        raise ValueError(
            f"OTP não validado ou expirado. Status atual: {reset_request.status}. "
            "É necessário validar o OTP antes de confirmar o reset."
        )
    
    # Resetar senha no Zoho
    if reset_request.system in ['zoho', 'both']:
        client = ZohoClient()
        try:
            success = client.reset_password(
                email=reset_request.identifier,
                new_password=new_password
            )
            
            if success:
                reset_request.status = 'completed'
                reset_request.completed_at = timezone.now()
                reset_request.save(update_fields=['status', 'completed_at'])
                
                logger.info(f"Senha resetada com sucesso para {reset_request.identifier}")
                return True
            else:
                # Não muda o status para 'failed' para permitir novas tentativas
                # O status permanece 'otp_validated' se já estava, ou volta para 'otp_validated'
                if reset_request.status != 'otp_validated':
                    reset_request.status = 'otp_validated'
                    reset_request.save(update_fields=['status'])
                raise ValueError("Falha ao resetar senha no Zoho")
                
        except ZohoException as e:
            # Não muda o status para 'failed' para permitir novas tentativas
            # O status permanece 'otp_validated' se já estava
            if reset_request.status != 'otp_validated':
                reset_request.status = 'otp_validated'
                reset_request.save(update_fields=['status'])
            logger.error(f"Erro ao resetar senha no Zoho: {e.message}")
            raise
    
    # TODO: Implementar reset no AD quando system for 'ad' ou 'both'
    if reset_request.system in ['ad', 'both']:
        logger.warning("Reset de senha no AD não implementado ainda")
        # raise NotImplementedError("Reset de senha no AD não implementado")
    
    return True

