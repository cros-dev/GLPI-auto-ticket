"""
Testes unitários para models.

Testa métodos auxiliares e lógica dos models:
- ZohoToken.is_access_token_valid()
- ZohoToken.needs_refresh()
- PasswordResetRequest.is_expired()
- PasswordResetRequest.generate_token()
- OtpToken.is_expired()
- OtpToken.has_exceeded_attempts()
- OtpToken.generate_code()
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import ZohoToken, PasswordResetRequest, OtpToken
from accounts.constants import MAX_OTP_ATTEMPTS


class ZohoTokenModelTest(TestCase):
    """Testes para métodos do model ZohoToken."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.zoho_token = ZohoToken.objects.create(
            refresh_token="test_refresh_token",
            access_token="test_access_token",
            expires_at=timezone.now() + timedelta(hours=1)
        )
    
    def test_is_access_token_valid_true(self):
        """Testa quando access token é válido."""
        # Act
        result = self.zoho_token.is_access_token_valid()
        
        # Assert
        self.assertTrue(result)
    
    def test_is_access_token_valid_expired(self):
        """Testa quando access token está expirado."""
        # Arrange
        self.zoho_token.expires_at = timezone.now() - timedelta(hours=1)
        self.zoho_token.save()
        
        # Act
        result = self.zoho_token.is_access_token_valid()
        
        # Assert
        self.assertFalse(result)
    
    def test_is_access_token_valid_no_token(self):
        """Testa quando access token não existe."""
        # Arrange
        self.zoho_token.access_token = None
        self.zoho_token.save()
        
        # Act
        result = self.zoho_token.is_access_token_valid()
        
        # Assert
        self.assertFalse(result)
    
    def test_is_access_token_valid_no_expires_at(self):
        """Testa quando expires_at não existe."""
        # Arrange
        self.zoho_token.expires_at = None
        self.zoho_token.save()
        
        # Act
        result = self.zoho_token.is_access_token_valid()
        
        # Assert
        self.assertFalse(result)
    
    def test_needs_refresh_when_valid(self):
        """Testa needs_refresh quando token é válido."""
        # Act
        result = self.zoho_token.needs_refresh()
        
        # Assert
        self.assertFalse(result)
    
    def test_needs_refresh_when_expired(self):
        """Testa needs_refresh quando token expirou."""
        # Arrange
        self.zoho_token.expires_at = timezone.now() - timedelta(hours=1)
        self.zoho_token.save()
        
        # Act
        result = self.zoho_token.needs_refresh()
        
        # Assert
        self.assertTrue(result)


class PasswordResetRequestModelTest(TestCase):
    """Testes para métodos do model PasswordResetRequest."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.reset_request = PasswordResetRequest(
            identifier="usuario@exemplo.com",
            system="zoho",
            status='pending'
        )
    
    def test_is_expired_false(self):
        """Testa quando solicitação não está expirada."""
        # Arrange
        self.reset_request.expires_at = timezone.now() + timedelta(hours=1)
        self.reset_request.save()
        
        # Act
        result = self.reset_request.is_expired()
        
        # Assert
        self.assertFalse(result)
    
    def test_is_expired_true(self):
        """Testa quando solicitação está expirada."""
        # Arrange
        self.reset_request.expires_at = timezone.now() - timedelta(hours=1)
        self.reset_request.save()
        
        # Act
        result = self.reset_request.is_expired()
        
        # Assert
        self.assertTrue(result)
    
    def test_generate_token_on_save(self):
        """Testa que token é gerado automaticamente no save."""
        # Act
        self.reset_request.save()
        
        # Assert
        self.assertIsNotNone(self.reset_request.token)
        self.assertEqual(len(self.reset_request.token), 43)  # token_urlsafe(32) = 43 chars
    
    def test_expires_at_set_on_save(self):
        """Testa que expires_at é configurado automaticamente no save."""
        # Act
        self.reset_request.save()
        
        # Assert
        self.assertIsNotNone(self.reset_request.expires_at)
        # Deve ser aproximadamente 1 hora no futuro
        expected_expires_at = timezone.now() + timedelta(hours=1)
        time_diff = abs((self.reset_request.expires_at - expected_expires_at).total_seconds())
        self.assertLess(time_diff, 5)


class OtpTokenModelTest(TestCase):
    """Testes para métodos do model OtpToken."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.reset_request = PasswordResetRequest.objects.create(
            identifier="usuario@exemplo.com",
            system="zoho",
            status='pending',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        self.otp_token = OtpToken(
            reset_request=self.reset_request,
            method='sms',
            status='pending'
        )
    
    def test_is_expired_false(self):
        """Testa quando OTP não está expirado."""
        # Arrange
        self.otp_token.expires_at = timezone.now() + timedelta(minutes=10)
        self.otp_token.save()
        
        # Act
        result = self.otp_token.is_expired()
        
        # Assert
        self.assertFalse(result)
    
    def test_is_expired_true(self):
        """Testa quando OTP está expirado."""
        # Arrange
        self.otp_token.expires_at = timezone.now() - timedelta(minutes=1)
        self.otp_token.save()
        
        # Act
        result = self.otp_token.is_expired()
        
        # Assert
        self.assertTrue(result)
    
    def test_has_exceeded_attempts_false(self):
        """Testa quando tentativas não foram excedidas."""
        # Arrange
        self.otp_token.attempts = 2
        self.otp_token.save()
        
        # Act
        result = self.otp_token.has_exceeded_attempts()
        
        # Assert
        self.assertFalse(result)
    
    def test_has_exceeded_attempts_true(self):
        """Testa quando tentativas foram excedidas."""
        # Arrange
        self.otp_token.attempts = MAX_OTP_ATTEMPTS
        self.otp_token.save()
        
        # Act
        result = self.otp_token.has_exceeded_attempts()
        
        # Assert
        self.assertTrue(result)
    
    def test_generate_code_on_save(self):
        """Testa que código é gerado automaticamente no save."""
        # Act
        self.otp_token.save()
        
        # Assert
        self.assertIsNotNone(self.otp_token.code)
        self.assertEqual(len(self.otp_token.code), 6)
        self.assertTrue(self.otp_token.code.isdigit())
    
    def test_expires_at_set_on_save(self):
        """Testa que expires_at é configurado automaticamente no save."""
        # Act
        self.otp_token.save()
        
        # Assert
        self.assertIsNotNone(self.otp_token.expires_at)
        # Deve ser aproximadamente 10 minutos no futuro
        expected_expires_at = timezone.now() + timedelta(minutes=10)
        time_diff = abs((self.otp_token.expires_at - expected_expires_at).total_seconds())
        self.assertLess(time_diff, 5)
    
    def test_increment_attempts(self):
        """Testa incremento de tentativas."""
        # Arrange
        self.otp_token.attempts = 1
        self.otp_token.save()
        
        # Act
        self.otp_token.increment_attempts()
        
        # Assert
        self.assertEqual(self.otp_token.attempts, 2)
    
    def test_increment_attempts_sets_exceeded_status(self):
        """Testa que status muda quando tentativas são excedidas."""
        # Arrange
        self.otp_token.attempts = 2
        self.otp_token.status = 'pending'
        self.otp_token.save()
        
        # Act
        self.otp_token.increment_attempts()
        
        # Assert
        self.assertEqual(self.otp_token.attempts, 3)
        self.assertEqual(self.otp_token.status, 'exceeded_attempts')

