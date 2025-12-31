# -*- coding: utf-8 -*-
"""
Script manual para testar busca de usuários no Zoho.

Este é um script de debug/teste manual, não um teste unitário formal.

COMO EXECUTAR:
    python manage.py shell
    exec(open('accounts/tests/test_zoho_user_search.py', encoding='utf-8').read())
"""
import traceback
from accounts.clients.zoho_client import ZohoClient
from accounts.exceptions import ZohoException
from django.conf import settings

print("=" * 60)
print("TESTE DE BUSCA DE USUÁRIO - ZOHO CLIENT")
print("=" * 60)

# Verificar configuracoes
print("\n1. Verificando configuracoes...")
client_id = getattr(settings, 'ZOHO_CLIENT_ID', None)
refresh_token = getattr(settings, 'ZOHO_REFRESH_TOKEN', None)
organization_id = getattr(settings, 'ZOHO_ORGANIZATION_ID', None)

if not client_id or not refresh_token:
    print("❌ ERRO: Configuracoes do Zoho nao encontradas no .env")
    print("   Configure ZOHO_CLIENT_ID e ZOHO_REFRESH_TOKEN")
    exit(1)

if not organization_id:
    print("⚠️  AVISO: ZOHO_ORGANIZATION_ID nao configurado")
    print("   A busca pode falhar se o zoid nao for encontrado")

# Testar inicializacao do client
print("\n2. Testando inicializacao do ZohoClient...")
try:
    client = ZohoClient()
    print("✅ OK: ZohoClient inicializado")
except Exception as e:
    print(f"❌ ERRO: {e}")
    exit(1)

# Loop interativo para buscar usuarios
print("\n" + "=" * 60)
print("MODO INTERATIVO - Busca de Usuários")
print("=" * 60)
print("\nDigite 'sair' ou 'exit' para encerrar")
print("Digite 'help' para ver opcoes disponiveis\n")

while True:
    email = input("Email do usuario (ou 'sair'/'help'): ").strip()
    
    if not email:
        print("   AVISO: Email vazio, tente novamente\n")
        continue
    
    if email.lower() in ['sair', 'exit', 'quit', 'q']:
        print("\nEncerrando teste...")
        break
    
    if email.lower() == 'help':
        print("\n" + "-" * 60)
        print("OPCOES DISPONIVEIS:")
        print("-" * 60)
        print("  • Digite um email para buscar o usuario completo")
        print("  • 'sair' ou 'exit' - Encerra o teste")
        print("  • 'help' - Mostra esta ajuda")
        print("-" * 60 + "\n")
        continue
    
    print(f"\n🔍 Buscando usuario: {email}")
    print("-" * 60)
    
    try:
        # Buscar dados completos do usuario
        user_data = client.get_user_by_email(email)
        
        if user_data:
            print("✅ USUARIO ENCONTRADO!")
            print("-" * 60)
            
            # Informacoes basicas
            zuid = user_data.get('zuid', 'N/A')
            display_name = user_data.get('displayName', 'N/A')
            first_name = user_data.get('firstName', 'N/A')
            last_name = user_data.get('lastName', 'N/A')
            primary_email = user_data.get('primaryEmailAddress', 'N/A')
            mailbox_address = user_data.get('mailboxAddress', 'N/A')
            
            print(f"📋 INFORMACOES BASICAS:")
            print(f"   ZUID: {zuid}")
            print(f"   Nome Completo: {display_name}")
            print(f"   Primeiro Nome: {first_name}")
            print(f"   Ultimo Nome: {last_name}")
            print(f"   Email Principal: {primary_email}")
            print(f"   Mailbox: {mailbox_address}")
            
            # Emails
            email_addresses = user_data.get('emailAddress', [])
            if email_addresses:
                print(f"\n📧 EMAILS ({len(email_addresses)}):")
                for idx, email_info in enumerate(email_addresses, 1):
                    mail_id = email_info.get('mailId', 'N/A')
                    is_primary = email_info.get('isPrimary', False)
                    is_alias = email_info.get('isAlias', False)
                    is_confirmed = email_info.get('isConfirmed', False)
                    primary_mark = " ⭐ PRINCIPAL" if is_primary else ""
                    alias_mark = " (Alias)" if is_alias else ""
                    confirmed_mark = " ✓" if is_confirmed else " ✗"
                    print(f"   {idx}. {mail_id}{primary_mark}{alias_mark}{confirmed_mark}")
            
            # Telefone
            phone = user_data.get('phoneNumber') or user_data.get('phoneNumer')
            mobile = user_data.get('mobileNumber')
            if phone or mobile:
                print(f"\n📱 CONTATO:")
                if phone:
                    print(f"   Telefone: {phone}")
                if mobile:
                    print(f"   Celular: {mobile}")
            
            # Status
            status = user_data.get('status')
            enabled = user_data.get('enabled')
            mailbox_status = user_data.get('mailboxStatus', 'N/A')
            print(f"\n⚙️  STATUS:")
            print(f"   Ativo: {'Sim' if status else 'Nao'}")
            print(f"   Habilitado: {'Sim' if enabled else 'Nao'}")
            print(f"   Status Mailbox: {mailbox_status}")
            
            # Grupos
            groups = user_data.get('groupList', [])
            if groups:
                print(f"\n👥 GRUPOS ({len(groups)}):")
                for idx, group in enumerate(groups, 1):
                    group_name = group.get('name', 'N/A')
                    group_email = group.get('emailId', 'N/A')
                    role = group.get('role', 'N/A')
                    print(f"   {idx}. {group_name} ({group_email}) - {role}")
            
            # Custom Fields
            custom_fields = user_data.get('customFields', [])
            if custom_fields:
                print(f"\n📝 CAMPOS PERSONALIZADOS ({len(custom_fields)}):")
                for field in custom_fields:
                    prop_name = field.get('propertyName', 'N/A')
                    prop_value = field.get('propertyValue', 'N/A')
                    print(f"   • {prop_name}: {prop_value}")
            
        else:
            print("❌ USUARIO NAO ENCONTRADO")
            print(f"   O email {email} nao existe na organizacao Zoho")
            
    except ZohoException as e:
        print(f"❌ ERRO ZOHO: {e.error_type}")
        print(f"   {e.message}")
        if e.error_type == 'unauthorized':
            print("   DICA: Verifique se o token tem permissao para buscar usuarios")
        elif e.error_type == 'forbidden':
            print("   DICA: Verifique os scopes do token")
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        traceback.print_exc()
    
    print("\n" + "-" * 60 + "\n")

print("\n" + "=" * 60)
print("TESTE CONCLUIDO")
print("=" * 60)

