# -*- coding: utf-8 -*-
"""
Script manual para testar reset de senha via ZohoClient.

Este é um script de debug/teste manual, não um teste unitário formal.

COMO EXECUTAR:
    python manage.py shell
    exec(open('accounts/tests/test_zoho_reset_password.py', encoding='utf-8').read())

IMPORTANTE:
    - Certifique-se de que o scope inclui: ZohoMail.organization.accounts.ALL ou UPDATE
    - Use um email de teste que existe no Zoho
    - A senha será realmente alterada no Zoho!
"""
import traceback
from accounts.clients.zoho_client import ZohoClient
from accounts.models import ZohoToken
from accounts.exceptions import ZohoException
from django.conf import settings

print("=" * 60)
print("TESTE DE RESET DE SENHA - ZOHO CLIENT")
print("=" * 60)

# Verificar configuracoes
print("\n1. Verificando configuracoes...")
client_id = getattr(settings, 'ZOHO_CLIENT_ID', None)
refresh_token = getattr(settings, 'ZOHO_REFRESH_TOKEN', None)

if not client_id or not refresh_token:
    print("❌ ERRO: Configuracoes do Zoho nao encontradas no .env")
    print("   Configure ZOHO_CLIENT_ID e ZOHO_REFRESH_TOKEN")
    exit(1)

# Verificar scope
print("\n2. Verificando scope do token...")
zoho_token = ZohoToken.objects.first()
if zoho_token:
    scope = zoho_token.scope
    print(f"   Scope atual: {scope}")
    
    if 'accounts.ALL' not in scope and 'accounts.UPDATE' not in scope:
        print("   AVISO: Scope pode nao ter permissao para reset de senha!")
        print("   Necessario: ZohoMail.organization.accounts.ALL ou UPDATE")
        print("   Se necessario, gere um novo refresh_token com scope correto")
else:
    print("   Token nao encontrado no banco")

# Testar inicializacao do client
print("\n3. Testando inicializacao do ZohoClient...")
try:
    client = ZohoClient()
    print("✅ OK: ZohoClient inicializado")
except Exception as e:
    print(f"❌ ERRO: {e}")
    exit(1)

# Solicitar email para teste
print("\n4. Buscando usuario pelo email...")
print("   (Digite um email de teste que existe no Zoho)")
email = input("   Email do usuario: ").strip()

if not email:
    print("❌ ERRO: Email nao fornecido")
    exit(1)

try:
    # Validar que usuário existe (reset_password também faz isso, mas é bom validar antes)
    user_data = client.get_user_by_email(email)
    if not user_data:
        print(f"❌ ERRO: Usuario {email} nao encontrado na organizacao")
        exit(1)
    
    zuid = user_data.get('zuid', 'N/A')
    print(f"✅ OK: Usuario encontrado!")
    print(f"   Email: {email}")
    print(f"   ZUID: {zuid}")
except ZohoException as e:
    print(f"❌ ERRO ZOHO: {e.error_type}")
    print(f"   {e.message}")
    exit(1)
except Exception as e:
    print(f"❌ ERRO: {e}")
    traceback.print_exc()
    exit(1)

# Testar reset de senha
print("\n5. Testando reset de senha...")
print("   ATENCAO: Isso vai realmente alterar a senha do usuario no Zoho!")
print("   Digite a nova senha (sera exibida na tela):")
new_password = input("   Nova senha: ").strip()

if not new_password:
    print("❌ ERRO: Senha nao fornecida")
    exit(1)

try:
    # reset_password busca o zuid automaticamente pelo email
    success = client.reset_password(email, new_password)
    if success:
        print(f"✅ OK: Senha resetada com sucesso para {email}!")
        print("   A senha foi alterada no Zoho")
    else:
        print("❌ ERRO: Reset de senha falhou")
except ZohoException as e:
    print(f"❌ ERRO ZOHO: {e.error_type}")
    print(f"   {e.message}")
    if e.error_type == 'forbidden' or e.error_type == 'insufficient_permissions':
        print("\n   DICA: Verifique se o scope inclui:")
        print("   - ZohoMail.organization.accounts.ALL")
        print("   - ou ZohoMail.organization.accounts.UPDATE")
        print("\n   Se necessario, gere um novo refresh_token com scope correto")
    traceback.print_exc()
except Exception as e:
    print(f"❌ ERRO: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("TESTE CONCLUIDO")
print("=" * 60)

