#!/usr/bin/env python3
"""
Test script to verify Keycloak configuration and connectivity
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_keycloak_config():
    print("Testing Keycloak Configuration...")
    print("=" * 50)
    
    # Check environment variables
    required_vars = [
        'KEYCLOAK_SERVER_URL',
        'KEYCLOAK_REALM', 
        'KEYCLOAK_CLIENT_ID',
        'KEYCLOAK_CLIENT_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: Missing")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing required variables: {', '.join(missing_vars)}")
        return False
    
    print("\n✅ All required environment variables are set")
    
    # Test Keycloak service initialization
    try:
        print("\nTesting KeycloakService initialization...")
        
        # Add the app directory to the path so we can import the service
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        
        from services.keycloak_service import KeycloakService
        
        keycloak_service = KeycloakService()
        print("✅ KeycloakService initialized successfully")
        
        # Test service availability
        print("\nTesting Keycloak service availability...")
        status = keycloak_service.get_service_status()
        
        print(f"Configured: {status['configured']}")
        print(f"Available: {status['available']}")
        print(f"Can access users: {status['can_access_users']}")
        
        if status['error']:
            print(f"Error: {status['error']}")
        
        if status['available']:
            print("✅ Keycloak service is available and accessible")
        else:
            print("❌ Keycloak service is not accessible")
        
        return status['available']
        
    except Exception as e:
        print(f"❌ Error testing KeycloakService: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_keycloak_config()
    if success:
        print("\n🎉 Keycloak configuration test passed!")
    else:
        print("\n💥 Keycloak configuration test failed!")
    
    sys.exit(0 if success else 1)
