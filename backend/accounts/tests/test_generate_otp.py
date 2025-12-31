"""
Testes unitários para generate_otp.

Testa a geração de códigos OTP, incluindo:
- Geração de código de 6 dígitos
- Expiração configurada
- Validação de status da solicitação
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import PasswordResetRequest, OtpToken
from accounts.services import generate_otp
from accounts.constants import OTP_EXPIRY_MINUTES


class GenerateOtpTest(TestCase):
    """Testes para generate_otp."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.reset_request = PasswordResetRequest.objects.create(
            identifier="usuario@exemplo.com",
            system="zoho",
            status='pending',
            expires_at=timezone.now() + timedelta(hours=1)
        )
    
    def test_generate_otp_success(self):
        """Testa geração bem-sucedida de OTP."""
        # Act
        otp_token = generate_otp(self.reset_request, method='sms')
        
        # Assert
        self.assertIsNotNone(otp_token)
        self.assertEqual(otp_token.reset_request, self.reset_request)
        self.assertEqual(otp_token.method, 'sms')
        self.assertEqual(otp_token.status, 'pending')
        self.assertEqual(len(otp_token.code), 6)
        self.assertTrue(otp_token.code.isdigit())
        self.assertIsNotNone(otp_token.expires_at)
        
        # Verifica que expires_at está configurado corretamente
        expected_expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        time_diff = abs((otp_token.expires_at - expected_expires_at).total_seconds())
        self.assertLess(time_diff, 5)
    
    def test_generate_otp_expired_request(self):
        """Testa geração de OTP quando solicitação está expirada."""
        # Arrange
        self.reset_request.expires_at = timezone.now() - timedelta(hours=1)
        self.reset_request.save()
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            generate_otp(self.reset_request)
        
        self.assertIn("expirada", str(context.exception).lower())
        
        # Verifica que status foi atualizado
        self.reset_request.refresh_from_db()
        self.assertEqual(self.reset_request.status, 'expired')
    
    def test_generate_otp_invalid_status(self):
        """Testa geração de OTP quando solicitação tem status inválido."""
        # Arrange
        self.reset_request.status = 'completed'
        self.reset_request.save()
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            generate_otp(self.reset_request)
        
        self.assertIn("status inválido", str(context.exception).lower())
    
    def test_generate_otp_allows_otp_validated_status(self):
        """Testa que geração de OTP permite status 'otp_validated' (para regenerar)."""
        # Arrange
        self.reset_request.status = 'otp_validated'
        self.reset_request.save()
        
        # Act
        otp_token = generate_otp(self.reset_request)
        
        # Assert
        self.assertIsNotNone(otp_token)
        self.assertEqual(otp_token.status, 'pending')
    
    def test_generate_otp_code_is_unique(self):
        """Testa que códigos OTP gerados são diferentes (não garante unicidade, mas testa geração)."""
        # Act
        otp_token1 = generate_otp(self.reset_request)
        otp_token2 = generate_otp(self.reset_request)
        
        # Assert - Pode ser igual por acaso, mas testa que ambos são válidos
        self.assertNotEqual(otp_token1.id, otp_token2.id)
        self.assertEqual(len(otp_token1.code), 6)
        self.assertEqual(len(otp_token2.code), 6)

