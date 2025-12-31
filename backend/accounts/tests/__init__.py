"""
Testes do app accounts (SSPR).

Este diretório contém:
- Testes unitários formais (herdam de TestCase):
  - test_request_password_reset.py - Testa solicitação de reset de senha
  - test_generate_otp.py - Testa geração de códigos OTP
  - test_validate_otp.py - Testa validação de códigos OTP
  - test_confirm_password_reset.py - Testa confirmação de reset de senha
  - test_models.py - Testa métodos auxiliares dos models
- Scripts de teste manual/debug:
  - test_zoho_user_search.py - Testa busca de usuários (interativo)
  - test_zoho_reset_password.py - Testa reset de senha via API
  - test_sms_client.py - Testa envio de SMS via Twilio
  - check_zoho_token.py - Verifica tokens Zoho no banco e .env
"""

