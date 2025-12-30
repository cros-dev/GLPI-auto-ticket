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
    print("ERRO: Configuracoes do Zoho nao encontradas no .env")
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
    print("OK: ZohoClient inicializado")
except Exception as e:
    print(f"ERRO: {e}")
    exit(1)

# Testar obtencao de organization ID
print("\n4. Testando obtencao de Organization ID (zoid)...")
try:
    zoid = client.get_organization_id()
    if zoid:
        print(f"OK: Organization ID obtido: {zoid}")
    else:
        print("ERRO: Nao foi possivel obter Organization ID")
        print("   Verifique se o token tem permissao ZohoMail.organization.READ")
        exit(1)
except ZohoException as e:
    print(f"ERRO: {e.error_type} - {e.message}")
    exit(1)
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Solicitar email para teste
print("\n5. Testando busca de User ID (zuid)...")
print("   (Digite um email de teste que existe no Zoho)")
email = input("   Email do usuario: ").strip()

if not email:
    print("ERRO: Email nao fornecido")
    exit(1)

try:
    zuid = client.get_user_id_by_email(email, zoid)
    if zuid:
        print(f"OK: User ID encontrado para {email}: {zuid}")
    else:
        print(f"ERRO: Usuario {email} nao encontrado na organizacao")
        exit(1)
except ZohoException as e:
    print(f"ERRO: {e.error_type} - {e.message}")
    exit(1)
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Testar validacao de usuario
print("\n6. Testando validacao de usuario...")
try:
    exists = client.validate_user(email)
    if exists:
        print(f"OK: Usuario {email} existe no Zoho")
    else:
        print(f"ERRO: Usuario {email} nao encontrado")
        exit(1)
except Exception as e:
    print(f"ERRO: {e}")
    exit(1)

# Testar reset de senha (OPCIONAL - requer confirmacao)
print("\n7. Testando reset de senha...")
print("   ATENCAO: Isso vai realmente alterar a senha do usuario no Zoho!")
confirm = input("   Deseja continuar? (sim/nao): ").strip().lower()

if confirm not in ['sim', 's', 'yes', 'y']:
    print("   Teste de reset de senha cancelado")
    print("\n" + "=" * 60)
    print("TESTE CONCLUIDO (sem reset de senha)")
    print("=" * 60)
    exit(0)

print("   Digite a nova senha (sera exibida na tela):")
new_password = input("   Nova senha: ").strip()

if not new_password:
    print("ERRO: Senha nao fornecida")
    exit(1)

try:
    success = client.reset_password(email, new_password)
    if success:
        print(f"OK: Senha resetada com sucesso para {email}!")
        print("   A senha foi alterada no Zoho")
    else:
        print("ERRO: Reset de senha falhou")
except ZohoException as e:
    print(f"ERRO: {e.error_type} - {e.message}")
    if e.error_type == 'forbidden':
        print("\n   DICA: Verifique se o scope inclui:")
        print("   - ZohoMail.organization.accounts.ALL")
        print("   - ou ZohoMail.organization.accounts.UPDATE")
        print("\n   Se necessario, gere um novo refresh_token com scope correto")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TESTE CONCLUIDO")
print("=" * 60)

