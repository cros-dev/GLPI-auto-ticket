"""
Constantes e configurações do app accounts (SSPR).

Centraliza todas as constantes usadas no módulo de autenticação e reset de senha.
"""

# Choices para sistemas (usado em PasswordResetRequest - pode resetar em ambos)
SYSTEM_CHOICES = [
    ('zoho', 'Zoho'),
    ('ad', 'Active Directory'),
    ('both', 'Zoho e AD'),
]

# Choices para sistemas individuais (usado em SystemAccount - uma conta por sistema)
SYSTEM_ACCOUNT_CHOICES = [
    ('zoho', 'Zoho'),
    ('ad', 'Active Directory'),
]

# Tempo de expiração padrão (em minutos)
OTP_EXPIRY_MINUTES = 10
RESET_REQUEST_EXPIRY_HOURS = 1

# Limites de tentativas
MAX_OTP_ATTEMPTS = 3
MAX_RESET_REQUESTS_PER_HOUR = 3

# Choices para métodos de OTP
OTP_METHOD_CHOICES = [
    ('sms', 'SMS'),
    ('email', 'Email'),
]

# Choices para status de tokens OTP
OTP_STATUS_CHOICES = [
    ('pending', 'Pendente'),
    ('validated', 'Validado'),
    ('expired', 'Expirado'),
    ('exceeded_attempts', 'Tentativas Excedidas'),
]

# Choices para status de solicitações de reset
RESET_REQUEST_STATUS_CHOICES = [
    ('pending', 'Pendente'),
    ('otp_validated', 'OTP Validado'),
    ('completed', 'Concluído'),
    ('expired', 'Expirado'),
    ('failed', 'Falhou'),
]

