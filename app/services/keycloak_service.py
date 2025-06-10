import os
import requests
import jwt
from urllib.parse import urlencode, quote


class KeycloakService:
    def __init__(self):
        self.server_url = os.getenv('KEYCLOAK_SERVER_URL')
        self.realm = os.getenv('KEYCLOAK_REALM')
        self.client_id = os.getenv('KEYCLOAK_CLIENT_ID')
        self.client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET')
        self.redirect_uri = os.getenv('KEYCLOAK_REDIRECT_URI')
        
        print(f"DEBUG: Keycloak config - server: {self.server_url}, realm: {self.realm}, client_id: {self.client_id}")
        
        if not all([self.server_url, self.realm, self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Missing Keycloak configuration")
        
        # Build base URLs
        self.base_url = f"{self.server_url}/realms/{self.realm}"
        self.auth_url = f"{self.base_url}/protocol/openid-connect/auth"
        self.token_url = f"{self.base_url}/protocol/openid-connect/token"
        self.userinfo_url = f"{self.base_url}/protocol/openid-connect/userinfo"
        self.logout_endpoint = f"{self.base_url}/protocol/openid-connect/logout"

    def get_auth_url(self):
        """Generate authorization URL for Keycloak"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'openid profile email'
        }
        
        url = f"{self.auth_url}?{urlencode(params)}"
        print(f"DEBUG: Auth URL: {url}")
        return url

    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        
        print(f"DEBUG: Token exchange data: {data}")
        
        try:
            response = requests.post(self.token_url, data=data)
            print(f"DEBUG: Token response status: {response.status_code}")
            print(f"DEBUG: Token response: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Token exchange failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Token exchange error: {str(e)}")
            return None

    def get_user_info(self, token):
        """Get user information from Keycloak"""
        headers = {
            'Authorization': f"Bearer {token['access_token']}"
        }
        
        try:
            response = requests.get(self.userinfo_url, headers=headers)
            print(f"DEBUG: Userinfo response status: {response.status_code}")
            
            if response.status_code == 200:
                user_info = response.json()
                print(f"DEBUG: Raw user info: {user_info}")
                return user_info
            else:
                print(f"Get user info failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Get user info error: {str(e)}")
            return None

    def validate_token(self, access_token):
        """Validate access token by making a request to userinfo endpoint"""
        headers = {
            'Authorization': f"Bearer {access_token}"
        }
        
        try:
            response = requests.get(self.userinfo_url, headers=headers)
            return response.status_code == 200
        except Exception as e:
            print(f"Token validation error: {str(e)}")
            return False

    def map_keycloak_roles_to_app_roles(self, user_info):
        """Map Keycloak roles to application roles"""
        print(f"DEBUG: Starting role mapping for user: {user_info.get('preferred_username')}")
        
        # Default role
        app_role = 'lector'
        
        # Check for resource_access with our client
        resource_access = user_info.get('resource_access', {})
        print(f"DEBUG: Resource access: {resource_access}")
        
        client_access = resource_access.get(self.client_id, {})
        print(f"DEBUG: Client access for '{self.client_id}': {client_access}")
        
        client_roles = client_access.get('roles', [])
        print(f"DEBUG: Client roles: {client_roles}")
        
        # Role mapping pr .
        # iority (highest to lowest)
        if 'admin' in client_roles:
            app_role = 'admin'
            print(f"DEBUG: User has admin role")
        elif 'depto-estudiantes' in client_roles:
            app_role = 'depto_estudiantes'
            print(f"DEBUG: User has depto-estudiantes role")
        elif 'evaluador' in client_roles:
            app_role = 'evaluador'
            print(f"DEBUG: User has evaluador role")
        else:
            # Default role
            app_role = 'lector'
            print(f"DEBUG: User has default lector role")
        
        print(f"DEBUG: Final mapped role: {app_role}")
        return app_role

    def logout_url(self, redirect_uri):
        """Generate logout URL for Keycloak"""
        params = {
            'client_id': self.client_id,
            'post_logout_redirect_uri': redirect_uri
        }
        
        url = f"{self.logout_endpoint}?{urlencode(params)}"
        print(f"DEBUG: Logout URL: {url}")
        return url

    def refresh_token(self, refresh_token):
        """Refresh access token using refresh token"""
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token
        }
        
        try:
            response = requests.post(self.token_url, data=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Token refresh failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Token refresh error: {str(e)}")
            return None

    def get_admin_token(self):
        """Get admin token for API access"""
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            response = requests.post(self.token_url, data=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Admin token failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Admin token error: {str(e)}")
            return None

    def get_users_by_role(self, role_name):
        """Get users by client role from Keycloak"""
        admin_token = self.get_admin_token()
        if not admin_token:
            print("Failed to get admin token")
            return []
        
        # Get client UUID first
        client_uuid = self.get_client_uuid(admin_token['access_token'])
        if not client_uuid:
            return []
        
        # Get users with the specific role
        url = f"{self.server_url}/admin/realms/{self.realm}/clients/{client_uuid}/roles/{role_name}/users"
        headers = {
            'Authorization': f"Bearer {admin_token['access_token']}",
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG: Get users by role response status: {response.status_code}")
            
            if response.status_code == 200:
                users = response.json()
                print(f"DEBUG: Found {len(users)} users with role {role_name}")
                return users
            else:
                print(f"Get users by role failed: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"Get users by role error: {str(e)}")
            return []

    def get_client_uuid(self, access_token):
        """Get the UUID of the client by client_id"""
        url = f"{self.server_url}/admin/realms/{self.realm}/clients"
        headers = {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params={'clientId': self.client_id})
            if response.status_code == 200:
                clients = response.json()
                if clients:
                    client_uuid = clients[0]['id']
                    print(f"DEBUG: Client UUID for {self.client_id}: {client_uuid}")
                    return client_uuid
                else:
                    print(f"Client {self.client_id} not found")
                    return None
            else:
                print(f"Get client UUID failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Get client UUID error: {str(e)}")
            return None

    def get_evaluadores(self):
        """Get all users with evaluador role and sync them to local database"""
        from app.models import Usuario
        from app import db
        
        print("DEBUG: Starting get_evaluadores - fetching from Keycloak")
        evaluadores_keycloak = self.get_users_by_role('evaluador')
        evaluadores_locales = []
        
        print(f"DEBUG: Found {len(evaluadores_keycloak)} evaluadores in Keycloak")
        
        for user_data in evaluadores_keycloak:
            print(f"DEBUG: Processing evaluador: {user_data.get('username')} ({user_data.get('email')})")
            
            # Check if user exists locally
            user = Usuario.query.filter_by(keycloak_id=user_data['id']).first()
            if not user:
                # Check by email as fallback
                user = Usuario.query.filter_by(email=user_data.get('email', '')).first()
            
            if not user and user_data.get('email'):
                # Create new user
                print(f"DEBUG: Creating new evaluador: {user_data.get('username')}")
                user = Usuario(
                    username=user_data.get('username', user_data.get('email')),
                    email=user_data.get('email'),
                    nombre=user_data.get('firstName', ''),
                    apellido=user_data.get('lastName', ''),
                    rol='evaluador',
                    keycloak_id=user_data['id'],
                    is_keycloak_user=True
                )
                db.session.add(user)
            elif user:
                # Update existing user
                print(f"DEBUG: Updating existing evaluador: {user.username}")
                user.keycloak_id = user_data['id']
                user.is_keycloak_user = True
                user.rol = 'evaluador'  # Ensure role is correct
                user.nombre = user_data.get('firstName', user.nombre)
                user.apellido = user_data.get('lastName', user.apellido)
                user.email = user_data.get('email', user.email)
            else:
                print(f"WARNING: Could not process evaluador {user_data.get('username')} - missing email")
                continue
            
            if user:
                evaluadores_locales.append(user)
        
        try:
            db.session.commit()
            print(f"DEBUG: Successfully synced {len(evaluadores_locales)} evaluadores from Keycloak")
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to sync evaluadores: {str(e)}")
            raise e
        
        return evaluadores_locales

    def get_available_evaluadores(self):
        """Get all available evaluators from Keycloak and sync them"""
        return self.get_evaluadores()
    
    def sync_all_evaluadores(self):
        """Sync all evaluadores from Keycloak to local database"""
        try:
            print("DEBUG: Starting sync_all_evaluadores")
            evaluadores = self.get_evaluadores()
            print(f"Successfully synced {len(evaluadores)} evaluadores from Keycloak")
            return evaluadores
        except Exception as e:
            print(f"Error syncing evaluadores: {str(e)}")
            return []

    def force_refresh_evaluadores(self):
        """Force refresh all evaluadores from Keycloak, removing local-only evaluadores"""
        from app.models import Usuario
        from app import db
        
        try:
            print("DEBUG: Starting force refresh of evaluadores")
            
            # Get fresh data from Keycloak
            keycloak_evaluadores = self.get_users_by_role('evaluador')
            keycloak_ids = [user['id'] for user in keycloak_evaluadores]
            
            # Remove local evaluadores that are no longer in Keycloak
            local_keycloak_evaluadores = Usuario.query.filter(
                Usuario.rol == 'evaluador',
                Usuario.is_keycloak_user == True,
                ~Usuario.keycloak_id.in_(keycloak_ids)
            ).all()
            
            for user in local_keycloak_evaluadores:
                print(f"DEBUG: Removing evaluador no longer in Keycloak: {user.username}")
                db.session.delete(user)
            
            # Sync current evaluadores
            evaluadores = self.get_evaluadores()
            
            db.session.commit()
            print(f"DEBUG: Force refresh completed. {len(evaluadores)} evaluadores synced")
            return evaluadores
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Force refresh failed: {str(e)}")
            raise e

    def is_service_available(self):
        """Check if Keycloak service is available and accessible"""
        try:
            admin_token = self.get_admin_token()
            return admin_token is not None
        except Exception as e:
            print(f"Keycloak service availability check failed: {str(e)}")
            return False

    def get_service_status(self):
        """Get detailed service status information"""
        status = {
            'configured': all([self.server_url, self.realm, self.client_id, self.client_secret]),
            'available': False,
            'can_access_users': False,
            'error': None
        }
        
        if not status['configured']:
            status['error'] = 'Incomplete Keycloak configuration'
            return status
        
        try:
            # Test admin token
            admin_token = self.get_admin_token()
            if admin_token:
                status['available'] = True
                
                # Test user access
                try:
                    evaluadores = self.get_users_by_role('evaluador')
                    status['can_access_users'] = True
                    status['evaluador_count'] = len(evaluadores)
                except Exception as e:
                    status['error'] = f'Cannot access users: {str(e)}'
            else:
                status['error'] = 'Cannot obtain admin token'
                
        except Exception as e:
            status['error'] = f'Service connection failed: {str(e)}'
        
        return status
