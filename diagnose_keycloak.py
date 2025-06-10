#!/usr/bin/env python3
"""
Keycloak Permissions Diagnostic Script
This script helps diagnose and fix Keycloak permission issues for the equivalencias app.
"""

import os
import sys
import requests
sys.path.append('.')

from app import create_app
from app.services.keycloak_service import KeycloakService

def check_keycloak_permissions():
    """Comprehensive check of Keycloak permissions and configuration"""
    print("🔍 KEYCLOAK PERMISSIONS DIAGNOSTIC")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            keycloak_service = KeycloakService()
            
            # Test 1: Basic configuration
            print("\n1️⃣ CONFIGURATION CHECK")
            config_items = [
                ("Server URL", keycloak_service.server_url),
                ("Realm", keycloak_service.realm),
                ("Client ID", keycloak_service.client_id),
                ("Client Secret", "***" if keycloak_service.client_secret else "❌ MISSING"),
                ("Redirect URI", keycloak_service.redirect_uri)
            ]
            
            for name, value in config_items:
                status = "✅" if value else "❌"
                print(f"   {status} {name}: {value}")
            
            # Test 2: Token acquisition
            print("\n2️⃣ TOKEN ACQUISITION")
            admin_token = keycloak_service.get_admin_token()
            if admin_token:
                print("   ✅ Admin token obtained successfully")
                print(f"   📄 Token type: {admin_token.get('token_type')}")
                print(f"   ⏱️  Expires in: {admin_token.get('expires_in')} seconds")
            else:
                print("   ❌ Failed to obtain admin token")
                return False
            
            # Test 3: Admin API Access
            print("\n3️⃣ ADMIN API ACCESS TEST")
            access_token = admin_token['access_token']
            
            # Test access to clients endpoint
            clients_url = f"{keycloak_service.server_url}/admin/realms/{keycloak_service.realm}/clients"
            headers = {
                'Authorization': f"Bearer {access_token}",
                'Content-Type': 'application/json'
            }
            
            response = requests.get(clients_url, headers=headers)
            print(f"   📡 Clients API Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Admin API access successful")
                clients = response.json()
                print(f"   📊 Found {len(clients)} clients in realm")
                
                # Find our specific client
                our_client = None
                for client in clients:
                    if client.get('clientId') == keycloak_service.client_id:
                        our_client = client
                        break
                
                if our_client:
                    print(f"   ✅ Found our client UUID: {our_client['id']}")
                    return test_user_access(keycloak_service, access_token, our_client['id'])
                else:
                    print(f"   ❌ Client '{keycloak_service.client_id}' not found in realm")
                    print("   💡 Check if client ID is correct")
                    
            elif response.status_code == 403:
                print("   ❌ 403 Forbidden - Insufficient permissions")
                print_permission_fix_instructions()
                return False
            else:
                print(f"   ❌ Unexpected error: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return False

def test_user_access(keycloak_service, access_token, client_uuid):
    """Test access to user data and roles"""
    print("\n4️⃣ USER AND ROLE ACCESS TEST")
    
    headers = {
        'Authorization': f"Bearer {access_token}",
        'Content-Type': 'application/json'
    }
    
    # Test 1: Access to users endpoint
    users_url = f"{keycloak_service.server_url}/admin/realms/{keycloak_service.realm}/users"
    response = requests.get(users_url, headers=headers, params={'max': 1})
    print(f"   📡 Users API Status: {response.status_code}")
    
    if response.status_code != 200:
        print("   ❌ Cannot access users endpoint")
        return False
    
    print("   ✅ Users endpoint accessible")
    
    # Test 2: Access to client roles
    roles_url = f"{keycloak_service.server_url}/admin/realms/{keycloak_service.realm}/clients/{client_uuid}/roles"
    response = requests.get(roles_url, headers=headers)
    print(f"   📡 Client Roles API Status: {response.status_code}")
    
    if response.status_code == 200:
        roles = response.json()
        print(f"   ✅ Found {len(roles)} client roles")
        
        # Check for required roles
        role_names = [role['name'] for role in roles]
        required_roles = ['admin', 'depto-estudiantes', 'evaluador', 'lector']
        
        print("   🎭 Role Check:")
        for role in required_roles:
            if role in role_names:
                print(f"      ✅ {role}")
            else:
                print(f"      ❌ {role} - MISSING")
        
        # Test 3: Access to users with evaluador role
        if 'evaluador' in role_names:
            print("\n   🔍 Testing evaluador role users...")
            evaluador_users_url = f"{keycloak_service.server_url}/admin/realms/{keycloak_service.realm}/clients/{client_uuid}/roles/evaluador/users"
            response = requests.get(evaluador_users_url, headers=headers)
            print(f"   📡 Evaluador Users API Status: {response.status_code}")
            
            if response.status_code == 200:
                evaluador_users = response.json()
                print(f"   ✅ Found {len(evaluador_users)} users with evaluador role")
                
                for user in evaluador_users[:3]:  # Show first 3 users
                    print(f"      👤 {user.get('username', 'N/A')} ({user.get('email', 'N/A')})")
                
                if len(evaluador_users) == 0:
                    print("   ⚠️  No users have the 'evaluador' role assigned")
                    print("   💡 Assign the 'evaluador' role to test users in Keycloak")
                
                return len(evaluador_users) > 0
            else:
                print(f"   ❌ Cannot access evaluador users: {response.text}")
                return False
        else:
            print("   ❌ 'evaluador' role not found - create it in client roles")
            return False
    else:
        print(f"   ❌ Cannot access client roles: {response.text}")
        return False

def print_permission_fix_instructions():
    """Print detailed instructions for fixing permissions"""
    print("\n🔧 PERMISSION FIX INSTRUCTIONS")
    print("=" * 50)
    print("The client needs admin permissions. Follow these steps:")
    print()
    print("1. Log into Keycloak Admin Console")
    print("2. Navigate to: Clients → equivalencias-app")
    print("3. Go to 'Service Account Roles' tab")
    print("4. In 'Client Roles' dropdown, select 'realm-management'")
    print("5. Add these roles to 'Assigned Roles':")
    print("   • view-users")
    print("   • view-clients")
    print("   • query-users")
    print("   • view-realm")
    print()
    print("6. If you need to modify users, also add:")
    print("   • manage-users")
    print()
    print("7. Save and run this test again")
    print()
    print("🔍 ADDITIONAL CHECKS:")
    print("• Ensure 'Service Accounts Enabled' is ON in client settings")
    print("• Verify client roles (admin, depto-estudiantes, evaluador, lector) exist")
    print("• Assign 'evaluador' role to test users")

def main():
    """Main diagnostic function"""
    success = check_keycloak_permissions()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Keycloak permissions are properly configured!")
        print("The application should now be able to retrieve evaluador users.")
    else:
        print("❌ ISSUES FOUND: Please follow the fix instructions above.")
        print("After making changes, run this script again to verify.")
    print("=" * 50)

if __name__ == "__main__":
    main()
