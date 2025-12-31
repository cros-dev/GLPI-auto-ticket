"""
Cliente para integração com Twilio SMS API.

Centraliza toda comunicação com a API do Twilio para envio de SMS, incluindo:
- Envio de códigos OTP via SMS
- Tratamento de erros e timeouts
"""
import logging
from typing import Optional
from django.conf import settings
from ..exceptions import SMSException
from ..parsers.sms_error_parser import parse_sms_error

logger = logging.getLogger(__name__)


class SMSClient:
    """
    Cliente para comunicação com Twilio SMS API.
    
    Encapsula toda lógica de envio de SMS usando Twilio Messages API.
    """
    
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        phone_number: Optional[str] = None
    ):
        """
        Inicializa o cliente SMS.
        
        Args:
            account_sid: Account SID do Twilio (ou obtém de settings)
            auth_token: Auth Token do Twilio (ou obtém de settings)
            phone_number: Número de telefone Twilio (ou obtém de settings)
        """
        self.account_sid = account_sid or getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = auth_token or getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.phone_number = phone_number or getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        self._client = None
    
    def _get_client(self):
        """
        Obtém ou cria o cliente Twilio.
        
        Returns:
            Twilio Rest Client ou None se configuração estiver incompleta
        """
        if not self.account_sid or not self.auth_token:
            return None
        
        if self._client is None:
            try:
                from twilio.rest import Client
                self._client = Client(self.account_sid, self.auth_token)
            except ImportError:
                logger.warning("Biblioteca twilio não instalada")
                return None
        
        return self._client
    
    def send_otp(
        self,
        phone_number: str,
        otp_code: str
    ) -> bool:
        """
        Envia código OTP via SMS usando Twilio Messages API.
        
        Args:
            phone_number: Número de telefone no formato internacional (ex: +5511999999999)
            otp_code: Código OTP de 6 dígitos a ser enviado
            
        Returns:
            bool: True se enviado com sucesso
            
        Raises:
            ValueError: Se configuração estiver incompleta
            SMSException: Se houver erro ao enviar SMS
        """
        if not self.account_sid or not self.auth_token:
            raise ValueError(
                "Configuração do Twilio incompleta. "
                "Verifique TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN no .env"
            )
        
        if not self.phone_number:
            raise ValueError(
                "TWILIO_PHONE_NUMBER não configurado no .env"
            )
        
        client = self._get_client()
        if not client:
            raise ValueError("Não foi possível criar cliente Twilio")
        
        try:
            message = client.messages.create(
                body=f"GRAM: Seu código de verificação é {otp_code}.",
                from_=self.phone_number,
                to=phone_number
            )
            
            logger.info(
                f"SMS OTP enviado via Twilio para {phone_number[:5]}*** "
                f"(Message SID: {message.sid})"
            )
            
            return True
            
        except Exception as e:
            error_type, error_message = parse_sms_error(e)
            logger.error(f"Erro ao enviar SMS via Twilio: {error_type} - {str(e)}")
            raise SMSException(error_type, error_message) from e
