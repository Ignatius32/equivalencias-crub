from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Usuario
from app import db
from werkzeug.security import check_password_hash
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already authenticated, redirect to appropriate dashboard
    if current_user.is_authenticated:
        return redirect_to_dashboard(current_user)
    
    use_keycloak = os.getenv('USE_KEYCLOAK', 'false').lower() == 'true'
    print(f"DEBUG: USE_KEYCLOAK = {os.getenv('USE_KEYCLOAK')}, use_keycloak = {use_keycloak}")
    
    if request.method == 'POST':
        if use_keycloak:
            # Redirect to Keycloak for authentication
            try:
                from app.services.keycloak_service import KeycloakService
                keycloak_service = KeycloakService()
                auth_url = keycloak_service.get_auth_url()
                return redirect(auth_url)
            except Exception as e:
                flash(f'Error de Keycloak: {str(e)}. Usando autenticación local.', 'warning')
                return handle_local_login()
        else:
            # Local authentication (existing logic)
            return handle_local_login()
    
    return render_template('auth/login.html', use_keycloak=use_keycloak)

@auth_bp.route('/callback')
def callback():
    """Handle Keycloak callback"""
    code = request.args.get('code')
    if not code:
        flash('Error de autenticación con Keycloak', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        from app.services.keycloak_service import KeycloakService
        keycloak_service = KeycloakService()
        
        # Exchange code for token
        token = keycloak_service.exchange_code_for_token(code)
        if not token:
            flash('Error al obtener token de Keycloak', 'danger')
            return redirect(url_for('auth.login'))
          # Get user info
        user_info = keycloak_service.get_user_info(token)
        if not user_info:
            flash('Error al obtener información del usuario', 'danger')
            return redirect(url_for('auth.login'))
        
        print(f"DEBUG: User info from Keycloak: {user_info}")
        
        # Map roles
        app_role = keycloak_service.map_keycloak_roles_to_app_roles(user_info)
        print(f"DEBUG: Mapped role: {app_role}")
        
        # Create or update user
        user = Usuario.create_or_update_from_keycloak(
            user_info, 
            user_info.get('sub'), 
            app_role
        )
        print(f"DEBUG: User created/updated: {user.username}, role: {user.rol}")
        
        # Store token in session
        session['access_token'] = token['access_token']
        session['refresh_token'] = token.get('refresh_token')
        
        # Login user
        login_user(user, remember=True)
        flash(f'{user.nombre}, te damos la bienvenida al Sistema de solicitudes de equivalencias.', 'success')
        
        return redirect_to_dashboard(user)
        
    except Exception as e:
        flash(f'Error al procesar usuario: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))

def handle_local_login():
    """Handle local authentication (existing logic)"""
    username = request.form.get('username')
    password = request.form.get('password')
    remember = 'remember' in request.form
    
    # Validación especial para el admin (acceso rápido)
    if username == 'admin' and password == 'admin':
        user = Usuario.query.filter_by(username='admin').first()
        if not user:
            # Crear usuario admin si no existe
            user = Usuario(
                username='admin',
                email='admin@crub.uncoma.edu.ar',
                nombre='Administrador',
                apellido='Sistema',
                rol='admin'
            )
            user.set_password('admin')
            db.session.add(user)
            db.session.commit()
        login_user(user, remember=remember)
        flash('Administrador, te damos la bienvenida al Sistema de solicitudes de equivalencias.', 'success')
        return redirect(url_for('admin.index'))
    
    # Validación especial para depto_estudiantes (acceso rápido)
    elif username == 'depto' and password == 'depto':
        user = Usuario.query.filter_by(username='depto').first()
        if not user:
            # Crear usuario depto_estudiantes si no existe
            user = Usuario(
                username='depto',
                email='depto_estudiantes@crub.uncoma.edu.ar',
                nombre='Departamento',
                apellido='Estudiantes',
                rol='depto_estudiantes'
            )
            user.set_password('depto')
            db.session.add(user)
            db.session.commit()
        login_user(user, remember=remember)
        flash('Departamento de Estudiantes, te damos la bienvenida al Sistema de solicitudes de equivalencias.', 'success')
        return redirect(url_for('depto.list_equivalencias'))
    
    # Proceso normal de login para otros usuarios
    user = Usuario.query.filter_by(username=username).first()
    
    if user and not user.is_keycloak_user and user.check_password(password):
        login_user(user, remember=remember)
        flash(f'{user.nombre}, te damos la bienvenida al Sistema de solicitudes de equivalencias.', 'success')
        return redirect_to_dashboard(user)
    
    flash('Usuario o contraseña incorrectos', 'danger')
    return redirect(url_for('auth.login'))

def redirect_to_dashboard(user):
    """Redirect user to appropriate dashboard based on role"""
    if user.rol == 'admin':
        return redirect(url_for('admin.index'))
    elif user.rol == 'depto_estudiantes':
        return redirect(url_for('depto.list_equivalencias'))
    elif user.rol == 'evaluador':
        return redirect(url_for('evaluadores.list_equivalencias'))
    elif user.rol == 'lector':
        return redirect(url_for('lector.list_equivalencias'))
    else:
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    use_keycloak = os.getenv('USE_KEYCLOAK', 'false').lower() == 'true'
    
    if use_keycloak and current_user.is_keycloak_user:
        # Keycloak logout
        try:
            from app.services.keycloak_service import KeycloakService
            keycloak_service = KeycloakService()
            logout_url = keycloak_service.logout_url(url_for('auth.login', _external=True))
            
            # Clear session
            session.clear()
            logout_user()
            
            flash('Sesión cerrada correctamente', 'success')
            return redirect(logout_url)
        except ImportError:
            pass  # Fall back to local logout
    
    # Local logout
    logout_user()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/force-logout')
def force_logout():
    """Force logout - clear all session data and redirect to Keycloak logout"""
    # Clear Flask session completely
    session.clear()
    
    # Logout user if logged in
    if current_user.is_authenticated:
        logout_user()
    
    use_keycloak = os.getenv('USE_KEYCLOAK', 'false').lower() == 'true'
    
    if use_keycloak:
        try:
            from app.services.keycloak_service import KeycloakService
            keycloak_service = KeycloakService()
            logout_url = keycloak_service.logout_url(url_for('auth.login', _external=True))
            
            flash('Sesión completamente cerrada', 'success')
            return redirect(logout_url)
        except Exception as e:
            flash(f'Error en logout de Keycloak: {str(e)}', 'warning')
    
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('auth.login'))
