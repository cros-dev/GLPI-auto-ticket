"""
Views da API REST para SSPR (Self-Service Password Reset).

Este módulo contém todas as views que expõem endpoints da API:
- Solicitação de reset de senha
- Validação de OTP
- Confirmação de reset de senha
"""
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .models import PasswordResetRequest
from .serializers import (
    PasswordResetRequestSerializer,
    PasswordResetRequestResponseSerializer,
    OtpValidationSerializer,
    OtpValidationResponseSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetConfirmResponseSerializer
)
from .services import (
    request_password_reset,
    generate_otp,
    send_otp_sms,
    validate_otp,
    confirm_password_reset
)
from .exceptions import ZohoException, SMSException

logger = logging.getLogger(__name__)


# =========================================================
# 1. SOLICITAÇÃO DE RESET DE SENHA
# =========================================================

class PasswordResetRequestView(APIView):
    """
    Cria uma solicitação de reset de senha e envia OTP via SMS.
    
    Endpoint: POST /api/accounts/password-reset/request/
    
    Valida se o usuário existe no sistema (Zoho), obtém telefone,
    gera OTP e envia via SMS.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Cria solicitação de reset e envia OTP."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        identifier = serializer.validated_data['identifier']
        system = serializer.validated_data.get('system', 'zoho')
        
        try:
            # Criar solicitação de reset (valida usuário e telefone)
            reset_request, phone_number = request_password_reset(identifier, system)
            
            if not phone_number:
                return Response(
                    {
                        'error': 'telefone_nao_encontrado',
                        'message': 'Número de telefone não encontrado no sistema. '
                                 'Verifique se o telefone está cadastrado no Zoho.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Gerar e enviar OTP
            otp_token = generate_otp(reset_request, method='sms')
            send_otp_sms(otp_token, phone_number)
            
            # Retornar resposta
            response_serializer = PasswordResetRequestResponseSerializer(reset_request)
            return Response(
                {
                    'message': 'Código OTP enviado via SMS',
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
            
        except ValueError as e:
            logger.warning(f"Erro ao criar solicitação de reset: {str(e)}")
            return Response(
                {
                    'error': 'validation_error',
                    'message': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except ZohoException as e:
            logger.error(f"Erro Zoho ao criar solicitação: {e.message}")
            return Response(
                {
                    'error': e.error_type,
                    'message': e.message
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except SMSException as e:
            logger.error(f"Erro SMS ao enviar OTP: {e.message}")
            return Response(
                {
                    'error': e.error_type,
                    'message': e.message
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro inesperado ao criar solicitação: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': 'internal_error',
                    'message': 'Erro interno ao processar solicitação. Tente novamente mais tarde.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =========================================================
# 2. VALIDAÇÃO DE OTP
# =========================================================

class OtpValidationView(APIView):
    """
    Valida código OTP recebido via SMS.
    
    Endpoint: POST /api/accounts/password-reset/validate-otp/
    
    Valida o código OTP informado pelo usuário. Se válido,
    a solicitação fica pronta para confirmar o reset.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Valida código OTP."""
        serializer = OtpValidationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        token = serializer.validated_data['token']
        otp_code = serializer.validated_data['otp_code']
        
        try:
            # Buscar solicitação
            try:
                reset_request = PasswordResetRequest.objects.get(token=token)
            except PasswordResetRequest.DoesNotExist:
                return Response(
                    {
                        'error': 'token_invalido',
                        'message': 'Token de solicitação inválido ou não encontrado.'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validar OTP
            is_valid = validate_otp(reset_request, otp_code)
            
            if is_valid:
                response_serializer = OtpValidationResponseSerializer({
                    'valid': True,
                    'token': token,
                    'message': 'OTP validado com sucesso. Você pode prosseguir com o reset de senha.'
                })
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {
                        'error': 'otp_invalido',
                        'message': 'Código OTP inválido. Verifique o código e tente novamente.',
                        'valid': False
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except ValueError as e:
            logger.warning(f"Erro ao validar OTP: {str(e)}")
            return Response(
                {
                    'error': 'validation_error',
                    'message': str(e),
                    'valid': False
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro inesperado ao validar OTP: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': 'internal_error',
                    'message': 'Erro interno ao validar OTP. Tente novamente mais tarde.',
                    'valid': False
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =========================================================
# 3. CONFIRMAÇÃO DE RESET DE SENHA
# =========================================================

class PasswordResetConfirmView(APIView):
    """
    Confirma e executa o reset de senha.
    
    Endpoint: POST /api/accounts/password-reset/confirm/
    
    Executa o reset de senha no sistema (Zoho) após validação do OTP.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Confirma e executa reset de senha."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            # Buscar solicitação
            try:
                reset_request = PasswordResetRequest.objects.get(token=token)
            except PasswordResetRequest.DoesNotExist:
                return Response(
                    {
                        'error': 'token_invalido',
                        'message': 'Token de solicitação inválido ou não encontrado.'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Confirmar reset de senha
            success = confirm_password_reset(reset_request, new_password)
            
            if success:
                response_serializer = PasswordResetConfirmResponseSerializer({
                    'success': True,
                    'message': 'Senha resetada com sucesso!',
                    'identifier': reset_request.identifier
                })
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {
                        'error': 'reset_falhou',
                        'message': 'Falha ao resetar senha. Tente novamente ou crie uma nova solicitação.',
                        'success': False
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except ValueError as e:
            logger.warning(f"Erro ao confirmar reset: {str(e)}")
            return Response(
                {
                    'error': 'validation_error',
                    'message': str(e),
                    'success': False
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except ZohoException as e:
            logger.error(f"Erro Zoho ao confirmar reset: {e.message}")
            return Response(
                {
                    'error': e.error_type,
                    'message': e.message,
                    'success': False
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro inesperado ao confirmar reset: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': 'internal_error',
                    'message': 'Erro interno ao resetar senha. Tente novamente mais tarde.',
                    'success': False
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
