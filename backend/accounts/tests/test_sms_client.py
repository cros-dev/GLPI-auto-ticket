# -*- coding: utf-8 -*-
"""
Script manual para testar envio de SMS via SMSClient (Twilio).

Este é um script de debug/teste manual, não um teste unitário formal.

COMO EXECUTAR:
    python manage.py shell
    exec(open('accounts/tests/test_sms_client.py', encoding='utf-8').read())

IMPORTANTE:
    - Certifique-se de que as variáveis TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN 
      e TWILIO_PHONE_NUMBER estão configuradas no .env
    - Use um número de telefone válido no formato internacional (ex: +5511999999999)
    - Este teste enviará um SMS real e pode gerar custos na conta Twilio
"""
import traceback
from accounts.clients.sms_client import SMSClient
from django.conf import settings

print("=" * 60)
print("TESTE DE ENVIO DE SMS - TWILIO CLIENT")
print("=" * 60)

# Verificar configurações
print("\n1. Verificando configurações...")
account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
phone_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

if not account_sid:
    print("❌ ERRO: TWILIO_ACCOUNT_SID não encontrado no .env")
    exit(1)

if not auth_token:
    print("❌ ERRO: TWILIO_AUTH_TOKEN não encontrado no .env")
    exit(1)

if not phone_number:
    print("❌ ERRO: TWILIO_PHONE_NUMBER não encontrado no .env")
    exit(1)

print("✅ OK: Configurações do Twilio encontradas")
print(f"   Account SID: {account_sid[:10]}...")
print(f"   Phone Number: {phone_number}")

# Testar inicialização do client
print("\n2. Testando inicialização do SMSClient...")
try:
    sms_client = SMSClient()
    print("✅ OK: SMSClient inicializado")
except Exception as e:
    print(f"❌ ERRO: {e}")
    traceback.print_exc()
    exit(1)

# Solicitar número de destino
print("\n3. Preparando envio de SMS...")
print("   Digite o número de telefone de destino (formato internacional)")
print("   Exemplo: +5511999999999")
print("   ⚠️ ATENÇÃO: Este teste enviará um SMS real e pode gerar custos!")
print("   Para cancelar, pressione Enter sem digitar nada")

destination = input("\n   Número de destino: ").strip()

if not destination:
    print("\n   ⚠️ Teste cancelado pelo usuário")
    exit(0)

# Validar formato básico
if not destination.startswith('+'):
    print(f"   ⚠️ AVISO: Número deve começar com '+' (formato internacional)")
    print(f"   Tentando adicionar...")
    if destination.startswith('55'):
        destination = '+' + destination
    else:
        destination = '+55' + destination
    print(f"   Número ajustado para: {destination}")

# Confirmar envio
print(f"\n   Você está prestes a enviar um SMS para: {destination}")
confirm = input("   Deseja continuar? (sim/nao): ").strip().lower()

if confirm not in ['sim', 's', 'yes', 'y']:
    print("\n   ⚠️ Teste cancelado pelo usuário")
    exit(0)

# Gerar código OTP de teste
import secrets
test_otp_code = f"{secrets.randbelow(1000000):06d}"

# Testar envio
print("\n4. Enviando SMS de teste...")
print(f"   Código OTP de teste: {test_otp_code}")
print(f"   Destino: {destination}")
print("   Aguarde...")

try:
    success = sms_client.send_otp(destination, test_otp_code)
    
    if success:
        print("\n✅ OK: SMS enviado com sucesso!")
        print(f"   O código {test_otp_code} foi enviado para {destination}")
        print("   Verifique o celular para confirmar o recebimento")
    else:
        print("\n❌ ERRO: Falha ao enviar SMS (retornou False)")
        
except ValueError as e:
    print(f"\n❌ ERRO DE VALIDAÇÃO: {e}")
    print("\n   DICA: Verifique:")
    print("   - Se TWILIO_ACCOUNT_SID está correto")
    print("   - Se TWILIO_AUTH_TOKEN está correto")
    print("   - Se TWILIO_PHONE_NUMBER está no formato correto (+5511999999999)")
    traceback.print_exc()
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    print("\n   DICA: Verifique:")
    print("   - Se a conta Twilio tem créditos/saldo")
    print("   - Se o número de destino está correto")
    print("   - Se o número Twilio está ativo")
    print("   - Logs do Twilio no console para mais detalhes")
    traceback.print_exc()

print("\n" + "=" * 60)
print("TESTE CONCLUÍDO")
print("=" * 60)

