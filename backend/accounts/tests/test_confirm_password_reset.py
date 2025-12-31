"""
Testes unitários para confirm_password_reset.

Testa a confirmação e execução do reset de senha, incluindo:
- Reset bem-sucedido
- Solicitação não validada
- Solicitação expirada
- Erro no Zoho
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import PasswordResetRequest
from accounts.services import confirm_password_reset
from accounts.exceptions import ZohoException


class ConfirmPasswordResetTest(TestCase):
    """Testes para confirm_password_reset."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.reset_request = PasswordResetRequest.objects.create(
            identifier="usuario@exemplo.com",
            system="zoho",
            status='otp_validated',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        self.new_password = "NovaSenh@123"
    
    @patch('accounts.services.ZohoClient')
    def test_confirm_password_reset_success(self, mock_zoho_client_class):
        """Testa confirmação bem-sucedida de reset de senha."""
        # Arrange
        mock_client = MagicMock()
        mock_client.reset_password.return_value = True
        mock_zoho_client_class.return_value = mock_client
        
        # Act
        result = confirm_password_reset(self.reset_request, self.new_password)
        
        # Assert
        self.assertTrue(result)
        mock_client.reset_password.assert_called_once_with(
            email=self.reset_request.identifier,
            new_password=self.new_password
        )
        
        self.reset_request.refresh_from_db()
        self.assertEqual(self.reset_request.status, 'completed')
        self.assertIsNotNone(self.reset_request.completed_at)
    
    def test_confirm_password_reset_not_validated(self):
        """Testa confirmação quando OTP não foi validado."""
        # Arrange
        self.reset_request.status = 'pending'
        self.reset_request.save()
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            confirm_password_reset(self.reset_request, self.new_password)
        
        self.assertIn("otp não validado", str(context.exception).lower())
        self.assertIn("otp_validated", str(context.exception))
    
    def test_confirm_password_reset_expired_request(self):
        """Testa confirmação quando solicitação está expirada."""
        # Arrange
        self.reset_request.expires_at = timezone.now() - timedelta(hours=1)
        self.reset_request.save()
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            confirm_password_reset(self.reset_request, self.new_password)
        
        self.assertIn("expirada", str(context.exception).lower())
        
        # Verifica que status foi atualizado
        self.reset_request.refresh_from_db()
        self.assertEqual(self.reset_request.status, 'expired')
    
    @patch('accounts.services.ZohoClient')
    def test_confirm_password_reset_zoho_failure(self, mock_zoho_client_class):
        """Testa confirmação quando Zoho retorna falha."""
        # Arrange
        mock_client = MagicMock()
        mock_client.reset_password.return_value = False
        mock_zoho_client_class.return_value = mock_client
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            confirm_password_reset(self.reset_request, self.new_password)
        
        self.assertIn("falha ao resetar senha", str(context.exception).lower())
        
        # Verifica que status foi atualizado
        self.reset_request.refresh_from_db()
        self.assertEqual(self.reset_request.status, 'failed')
    
    @patch('accounts.services.ZohoClient')
    def test_confirm_password_reset_zoho_exception(self, mock_zoho_client_class):
        """Testa confirmação quando Zoho levanta exceção."""
        # Arrange
        mock_client = MagicMock()
        mock_client.reset_password.side_effect = ZohoException(
            'api_error',
            'Erro ao resetar senha'
        )
        mock_zoho_client_class.return_value = mock_client
        
        # Act & Assert
        with self.assertRaises(ZohoException) as context:
            confirm_password_reset(self.reset_request, self.new_password)
        
        self.assertEqual(context.exception.error_type, 'api_error')
        self.assertIn('Erro ao resetar senha', context.exception.message)
        
        # Verifica que status foi atualizado
        self.reset_request.refresh_from_db()
        self.assertEqual(self.reset_request.status, 'failed')
    
    @patch('accounts.services.ZohoClient')
    def test_confirm_password_reset_system_both(self, mock_zoho_client_class):
        """Testa confirmação quando system é 'both'."""
        # Arrange
        self.reset_request.system = 'both'
        self.reset_request.save()
        
        mock_client = MagicMock()
        mock_client.reset_password.return_value = True
        mock_zoho_client_class.return_value = mock_client
        
        # Act
        result = confirm_password_reset(self.reset_request, self.new_password)
        
        # Assert
        self.assertTrue(result)
        mock_client.reset_password.assert_called_once()

