"""
Testes unitários para validate_otp.

Testa a validação de códigos OTP, incluindo:
- Validação bem-sucedida
- Código inválido
- OTP expirado
- Tentativas excedidas
- Solicitação expirada
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import PasswordResetRequest, OtpToken
from accounts.services import validate_otp


class ValidateOtpTest(TestCase):
    """Testes para validate_otp."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.reset_request = PasswordResetRequest.objects.create(
            identifier="usuario@exemplo.com",
            system="zoho",
            status='pending',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        self.otp_token = OtpToken.objects.create(
            reset_request=self.reset_request,
            method='sms',
            status='pending',
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
    
    def test_validate_otp_success(self):
        """Testa validação bem-sucedida de OTP."""
        # Act
        result = validate_otp(self.reset_request, '123456')
        
        # Assert
        self.assertTrue(result)
        self.otp_token.refresh_from_db()
        self.assertEqual(self.otp_token.status, 'validated')
        self.assertIsNotNone(self.otp_token.validated_at)
        
        self.reset_request.refresh_from_db()
        self.assertEqual(self.reset_request.status, 'otp_validated')
    
    def test_validate_otp_invalid_code(self):
        """Testa validação com código OTP inválido."""
        # Act
        result = validate_otp(self.reset_request, '999999')
        
        # Assert
        self.assertFalse(result)
        self.otp_token.refresh_from_db()
        self.assertEqual(self.otp_token.status, 'pending')
        self.assertEqual(self.otp_token.attempts, 1)
        self.assertIsNone(self.otp_token.validated_at)
    
    def test_validate_otp_invalid_code_increments_attempts(self):
        """Testa que código inválido incrementa tentativas."""
        # Arrange
        initial_attempts = self.otp_token.attempts
        
        # Act
        validate_otp(self.reset_request, '999999')
        
        # Assert
        self.otp_token.refresh_from_db()
        self.assertEqual(self.otp_token.attempts, initial_attempts + 1)
    
    def test_validate_otp_exceeds_attempts(self):
        """Testa que após 3 tentativas inválidas, OTP fica bloqueado."""
        # Arrange - Simular 3 tentativas falhas
        self.otp_token.attempts = 3
        self.otp_token.save()
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            validate_otp(self.reset_request, '123456')
        
        self.assertIn("tentativas excedidas", str(context.exception).lower())
    
    def test_validate_otp_expired_token(self):
        """Testa validação quando OTP está expirado."""
        # Arrange
        self.otp_token.expires_at = timezone.now() - timedelta(minutes=1)
        self.otp_token.save()
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            validate_otp(self.reset_request, '123456')
        
        self.assertIn("expirado", str(context.exception).lower())
        
        # Verifica que status foi atualizado
        self.otp_token.refresh_from_db()
        self.assertEqual(self.otp_token.status, 'expired')
    
    def test_validate_otp_expired_request(self):
        """Testa validação quando solicitação está expirada."""
        # Arrange
        self.reset_request.expires_at = timezone.now() - timedelta(hours=1)
        self.reset_request.save()
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            validate_otp(self.reset_request, '123456')
        
        self.assertIn("expirada", str(context.exception).lower())
        
        # Verifica que status foi atualizado
        self.reset_request.refresh_from_db()
        self.assertEqual(self.reset_request.status, 'expired')
    
    def test_validate_otp_no_pending_token(self):
        """Testa validação quando não há OTP pendente."""
        # Arrange
        self.otp_token.status = 'validated'
        self.otp_token.save()
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            validate_otp(self.reset_request, '123456')
        
        self.assertIn("nenhum otp pendente", str(context.exception).lower())
    
    def test_validate_otp_code_stripped(self):
        """Testa que código OTP com espaços é tratado corretamente."""
        # Act
        result = validate_otp(self.reset_request, '  123456  ')
        
        # Assert
        self.assertTrue(result)
    
    def test_validate_otp_most_recent_token_used(self):
        """Testa que o OTP mais recente é usado quando há múltiplos."""
        # Arrange - Criar outro OTP mais recente
        newer_otp = OtpToken.objects.create(
            reset_request=self.reset_request,
            method='sms',
            status='pending',
            code='654321',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Act
        result = validate_otp(self.reset_request, '654321')
        
        # Assert
        self.assertTrue(result)
        newer_otp.refresh_from_db()
        self.assertEqual(newer_otp.status, 'validated')
        
        # OTP antigo não deve ser validado
        self.otp_token.refresh_from_db()
        self.assertEqual(self.otp_token.status, 'pending')

