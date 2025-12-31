# -*- coding: utf-8 -*-
"""
Script para verificar e comparar tokens Zoho no banco e .env.

COMO EXECUTAR:
    python manage.py shell
    exec(open('accounts/tests/check_zoho_token.py', encoding='utf-8').read())
"""
from accounts.models import ZohoToken
from django.conf import settings

print("=" * 60)
print("VERIFICAÇÃO DE TOKENS ZOHO")
print("=" * 60)

# Verificar no .env
print("\n1. Tokens no .env:")
env_client_id = getattr(settings, 'ZOHO_CLIENT_ID', None)
env_client_secret = getattr(settings, 'ZOHO_CLIENT_SECRET', None)
env_refresh_token = getattr(settings, 'ZOHO_REFRESH_TOKEN', None)

print(f"   CLIENT_ID: {env_client_id[:20] if env_client_id else 'None'}... (tamanho: {len(env_client_id) if env_client_id else 0})")
print(f"   CLIENT_SECRET: {'***' if env_client_secret else 'None'} (tamanho: {len(env_client_secret) if env_client_secret else 0})")
print(f"   REFRESH_TOKEN: {env_refresh_token[:30] if env_refresh_token else 'None'}... (tamanho: {len(env_refresh_token) if env_refresh_token else 0})")

# Verificar no banco
print("\n2. Tokens no banco:")
zoho_token = ZohoToken.objects.first()

if zoho_token:
    print(f"   ID: {zoho_token.id}")
    print(f"   REFRESH_TOKEN: {zoho_token.refresh_token[:30]}... (tamanho: {len(zoho_token.refresh_token)})")
    print(f"   ACCESS_TOKEN: {'Existe' if zoho_token.access_token else 'None'} (tamanho: {len(zoho_token.access_token) if zoho_token.access_token else 0})")
    print(f"   EXPIRES_AT: {zoho_token.expires_at}")
    print(f"   SCOPE: {zoho_token.scope}")
    print(f"   API_DOMAIN: {zoho_token.api_domain}")
    print(f"   Criado em: {zoho_token.created_at}")
    print(f"   Atualizado em: {zoho_token.updated_at}")
    
    # Comparar refresh tokens
    print("\n3. Comparação:")
    if env_refresh_token and zoho_token.refresh_token:
        if env_refresh_token == zoho_token.refresh_token:
            print("   ✅ REFRESH_TOKEN do .env é IGUAL ao do banco")
        else:
            print("   ❌ REFRESH_TOKEN do .env é DIFERENTE do banco!")
            print(f"      .env: {env_refresh_token[:50]}...")
            print(f"      Banco: {zoho_token.refresh_token[:50]}...")
    
    # Verificar se access token é válido
    print("\n4. Status do Access Token:")
    if zoho_token.is_access_token_valid():
        print("   ✅ Access token é VÁLIDO")
        print(f"      Expira em: {zoho_token.expires_at}")
    else:
        print("   ❌ Access token é INVÁLIDO ou EXPIRADO")
        if zoho_token.expires_at:
            print(f"      Expirou em: {zoho_token.expires_at}")
        else:
            print("      Nunca foi definido")
else:
    print("   ❌ Nenhum token encontrado no banco!")

print("\n" + "=" * 60)
print("RECOMENDAÇÕES:")
print("=" * 60)
print("1. Se o refresh token está inválido, gere um novo:")
print("   - Acesse: https://api-console.zoho.com/")
print("   - Gere um novo authorization code")
print("   - Troque por refresh_token + access_token")
print("   - Atualize o ZOHO_REFRESH_TOKEN no .env")
print("\n2. Se o token no banco está diferente do .env:")
print("   - Delete o token do banco (via admin ou shell)")
print("   - O ZohoClient criará um novo automaticamente do .env")
print("\n3. Para deletar token do banco:")
print("   ZohoToken.objects.all().delete()")

