#!/usr/bin/env python3
import os
import sys
sys.path.append('.')

from app import create_app
from app.services.keycloak_service import KeycloakService
from app.services.evaluador_service import EvaluadorService

def test_keycloak_connection():
    app = create_app()
    
    with app.app_context():
        print("=== Keycloak Configuration ===")
        print(f"KEYCLOAK_SERVER_URL: {os.getenv('KEYCLOAK_SERVER_URL')}")
        print(f"KEYCLOAK_REALM: {os.getenv('KEYCLOAK_REALM')}")
        print(f"KEYCLOAK_CLIENT_ID: {os.getenv('KEYCLOAK_CLIENT_ID')}")
        print(f"KEYCLOAK_CLIENT_SECRET: {'***' if os.getenv('KEYCLOAK_CLIENT_SECRET') else 'None'}")
        print(f"KEYCLOAK_REDIRECT_URI: {os.getenv('KEYCLOAK_REDIRECT_URI')}")
        print()
        
        print("=== Testing KeycloakService ===")
        try:
            keycloak_service = KeycloakService()
            print("✓ KeycloakService initialized successfully")
            
            # Test service status
            print("Testing service status...")
            status = keycloak_service.get_service_status()
            print(f"  - Configured: {status['configured']}")
            print(f"  - Available: {status['available']}")
            print(f"  - Can access users: {status['can_access_users']}")
            if status['error']:
                print(f"  - Error: {status['error']}")
            if 'evaluador_count' in status:
                print(f"  - Evaluador count: {status['evaluador_count']}")
            print()
            
            # Test admin token
            print("Testing admin token...")
            admin_token = keycloak_service.get_admin_token()
            if admin_token:
                print("✓ Admin token obtained successfully")
                print(f"  Token type: {admin_token.get('token_type', 'unknown')}")
                print(f"  Expires in: {admin_token.get('expires_in', 'unknown')} seconds")
            else:
                print("✗ Failed to get admin token")
                return
            
            # Test client UUID retrieval specifically
            print("Testing client UUID retrieval...")
            client_uuid = keycloak_service.get_client_uuid(admin_token['access_token'])
            if client_uuid:
                print(f"✓ Client UUID obtained: {client_uuid}")
            else:
                print("✗ Failed to get client UUID - this indicates insufficient admin permissions")
                print("  The client needs 'realm-management' or 'view-clients' role")
            
            # Test getting evaluadores
            print("Testing get_evaluadores...")
            evaluadores = keycloak_service.get_evaluadores()
            print(f"Found {len(evaluadores)} evaluadores from Keycloak")
            
            for ev in evaluadores:
                print(f"  - {ev.username} ({ev.email}) - Role: {ev.rol}")
                
        except Exception as e:
            print(f"✗ Error with KeycloakService: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n=== Testing EvaluadorService ===")
        try:
            evaluador_service = EvaluadorService()
            print("✓ EvaluadorService initialized successfully")
            
            # Test service status
            print("Testing EvaluadorService status...")
            service_status = evaluador_service.get_service_status()
            print(f"  - Keycloak enabled: {service_status['keycloak_enabled']}")
            print(f"  - Local evaluadores: {service_status['local_evaluadores']}")
            print(f"  - Keycloak evaluadores: {service_status['keycloak_evaluadores']}")
            if service_status['keycloak_status']:
                kc_status = service_status['keycloak_status']
                print(f"  - Keycloak status: {kc_status}")
            print()
            
            evaluadores = evaluador_service.get_all_evaluadores()
            print(f"✓ Found {len(evaluadores)} evaluadores through EvaluadorService")
            
            evaluadores_with_workload = evaluador_service.get_evaluadores_with_workload(auto_sync=False)  # Disable auto-sync for testing
            print(f"✓ Found {len(evaluadores_with_workload)} evaluadores with workload info")
            
            for item in evaluadores_with_workload:
                ev = item['evaluador']
                print(f"  - {ev.username} ({ev.email}) - Role: {ev.rol} - Workload: {item['workload']} active, {item['total_assigned']} total - Keycloak User: {ev.is_keycloak_user}")
                
        except Exception as e:
            print(f"✗ Error with EvaluadorService: {str(e)}")
            import traceback
            traceback.print_exc()

def test_specific_client_permissions():
    """Test specific client permissions and roles"""
    print("\n=== Testing Client Permissions ===")
    
    try:
        app = create_app()
        with app.app_context():
            keycloak_service = KeycloakService()
            
            # Get admin token
            admin_token = keycloak_service.get_admin_token()
            if not admin_token:
                print("✗ Cannot get admin token")
                return
            
            # Try to list all clients to see if we have proper permissions
            import requests
            url = f"{keycloak_service.server_url}/admin/realms/{keycloak_service.realm}/clients"
            headers = {
                'Authorization': f"Bearer {admin_token['access_token']}",
                'Content-Type': 'application/json'
            }
            
            print("Testing access to admin API...")
            response = requests.get(url, headers=headers)
            print(f"  - Admin API access status: {response.status_code}")
            
            if response.status_code == 200:
                clients = response.json()
                print(f"  - Found {len(clients)} clients in realm")
                
                # Find our client
                our_client = None
                for client in clients:
                    if client.get('clientId') == keycloak_service.client_id:
                        our_client = client
                        break
                
                if our_client:
                    print(f"  ✓ Found our client: {our_client['id']}")
                    print(f"    - Client ID: {our_client['clientId']}")
                    print(f"    - Client UUID: {our_client['id']}")
                else:
                    print(f"  ✗ Could not find client '{keycloak_service.client_id}' in the realm")
            elif response.status_code == 403:
                print("  ✗ 403 Forbidden - Client lacks admin permissions")
                print("    Solution: In Keycloak admin console:")
                print("    1. Go to Clients > equivalencias-app > Service Account Roles")
                print("    2. Add 'realm-management' client role")
                print("    3. Or add specific roles: view-users, view-clients, query-users")
            else:
                print(f"  ✗ Unexpected response: {response.status_code} - {response.text}")
                
    except Exception as e:
        print(f"✗ Error testing client permissions: {str(e)}")

if __name__ == "__main__":
    test_keycloak_connection()
    test_specific_client_permissions()
