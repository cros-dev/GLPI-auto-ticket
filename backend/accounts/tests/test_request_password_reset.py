"""
Testes unitários para request_password_reset.

Testa a funcionalidade de solicitação de reset de senha, incluindo:
- Validação de limites
- Validação de sistema
- Busca de telefone no Zoho
- Criação de solicitação
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import PasswordResetRequest
from accounts.services import request_password_reset
from accounts.exceptions import ZohoException
from accounts.constants import MAX_RESET_REQUESTS_PER_HOUR, RESET_REQUEST_EXPIRY_HOURS


class RequestPasswordResetTest(TestCase):
    """Testes para request_password_reset."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.identifier = "usuario@exemplo.com"
        self.system = "zoho"
        self.phone_number = "+5511999999999"
    
    @patch('accounts.services.ZohoClient')
    def test_request_password_reset_success(self, mock_zoho_client_class):
        """Testa solicitação bem-sucedida de reset de senha."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_user_phone_by_email.return_value = self.phone_number
        mock_zoho_client_class.return_value = mock_client
        
        # Act
        reset_request, phone_number = request_password_reset(
            self.identifier,
            self.system
        )
        
        # Assert
        self.assertIsNotNone(reset_request)
        self.assertEqual(reset_request.identifier, self.identifier)
        self.assertEqual(reset_request.system, self.system)
        self.assertEqual(reset_request.status, 'pending')
        self.assertEqual(phone_number, self.phone_number)
        self.assertIsNotNone(reset_request.token)
        self.assertIsNotNone(reset_request.expires_at)
        mock_client.get_user_phone_by_email.assert_called_once_with(self.identifier)
    
    def test_request_password_reset_invalid_system(self):
        """Testa solicitação com sistema inválido."""
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            request_password_reset(self.identifier, "invalid_system")
        
        self.assertIn("Sistema inválido", str(context.exception))
    
    @patch('accounts.services.ZohoClient')
    def test_request_password_reset_user_not_found(self, mock_zoho_client_class):
        """Testa solicitação quando usuário não é encontrado no Zoho."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_user_phone_by_email.return_value = None
        mock_zoho_client_class.return_value = mock_client
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            request_password_reset(self.identifier, self.system)
        
        self.assertIn("não encontrado", str(context.exception).lower())
        self.assertIn("telefone", str(context.exception).lower())
    
    @patch('accounts.services.ZohoClient')
    def test_request_password_reset_zoho_exception(self, mock_zoho_client_class):
        """Testa solicitação quando Zoho retorna erro."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_user_phone_by_email.side_effect = ZohoException(
            'api_error',
            'Erro ao buscar usuário'
        )
        mock_zoho_client_class.return_value = mock_client
        
        # Act & Assert
        with self.assertRaises(ZohoException) as context:
            request_password_reset(self.identifier, self.system)
        
        self.assertEqual(context.exception.error_type, 'api_error')
        self.assertIn('Erro ao buscar usuário', context.exception.message)
    
    def test_request_password_reset_rate_limit_exceeded(self):
        """Testa limite de solicitações por hora."""
        # Arrange - Criar solicitações até o limite
        for i in range(MAX_RESET_REQUESTS_PER_HOUR):
            PasswordResetRequest.objects.create(
                identifier=self.identifier,
                system=self.system,
                status='pending',
                expires_at=timezone.now() + timedelta(hours=RESET_REQUEST_EXPIRY_HOURS)
            )
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            request_password_reset(self.identifier, self.system)
        
        self.assertIn("Limite", str(context.exception))
        self.assertIn(str(MAX_RESET_REQUESTS_PER_HOUR), str(context.exception))
    
    @patch('accounts.services.ZohoClient')
    def test_request_password_reset_expires_at_set(self, mock_zoho_client_class):
        """Testa se expires_at é configurado corretamente."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_user_phone_by_email.return_value = self.phone_number
        mock_zoho_client_class.return_value = mock_client
        
        # Act
        reset_request, _ = request_password_reset(self.identifier, self.system)
        
        # Assert
        expected_expires_at = timezone.now() + timedelta(hours=RESET_REQUEST_EXPIRY_HOURS)
        # Permitir diferença de até 5 segundos devido ao tempo de execução
        time_diff = abs((reset_request.expires_at - expected_expires_at).total_seconds())
        self.assertLess(time_diff, 5)

