# -*- coding: utf-8 -*-
"""
Script manual para testar ZohoClient.

Este é um script de debug/teste manual, não um teste unitário formal.
Para testes unitários, use accounts/tests/test_zoho_client.py (futuro).

COMO EXECUTAR:
    python manage.py shell
    exec(open('accounts/tests/test_zoho_client_manual.py', encoding='utf-8').read())
"""
from accounts.clients.zoho_client import ZohoClient
from accounts.models import ZohoToken
from django.conf import settings

print("=" * 60)
print("TESTE DO ZOHO CLIENT")
print("=" * 60)

# Verificar configuracoes
print("\n1. Verificando configuracoes...")
client_id = getattr(settings, 'ZOHO_CLIENT_ID', None)
client_secret = getattr(settings, 'ZOHO_CLIENT_SECRET', None)
refresh_token = getattr(settings, 'ZOHO_REFRESH_TOKEN', None)

if not client_id:
    print("ERRO: ZOHO_CLIENT_ID nao configurado no .env")
elif not client_secret:
    print("ERRO: ZOHO_CLIENT_SECRET nao configurado no .env")
elif not refresh_token:
    print("ERRO: ZOHO_REFRESH_TOKEN nao configurado no .env")
else:
    print("OK: Todas as variaveis estao configuradas")
    print(f"   Client ID: {client_id[:10]}...")
    print(f"   Refresh Token: {refresh_token[:20]}...")

# Verificar token no banco
print("\n2. Verificando token no banco...")
zoho_token = ZohoToken.objects.first()
if zoho_token:
    print("OK: Token encontrado no banco")
    print(f"   Refresh Token: {zoho_token.refresh_token[:20]}...")
    if zoho_token.access_token:
        print(f"   Access Token: {zoho_token.access_token[:20]}...")
        print(f"   Valido: {'Sim' if zoho_token.is_access_token_valid() else 'Nao'}")
else:
    print("AVISO: Token nao encontrado - sera criado automaticamente")

# Testar client
print("\n3. Testando ZohoClient...")
try:
    client = ZohoClient()
    access_token = client.get_access_token()
    if access_token:
        print("OK: Access token obtido com sucesso!")
        print(f"   Token: {access_token[:30]}...")
        
        # Verificar no banco
        zoho_token = ZohoToken.objects.first()
        if zoho_token and zoho_token.access_token:
            print(f"OK: Token salvo no banco")
            print(f"   Expira em: {zoho_token.expires_at}")
    else:
        print("ERRO: Nao foi possivel obter access token")
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)

