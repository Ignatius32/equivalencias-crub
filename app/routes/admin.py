from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import Usuario, SolicitudEquivalencia
from app import db
from app.services.google_drive_service import GoogleDriveService
from app.services.evaluador_service import EvaluadorService
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorador para verificar si el usuario es administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Se requieren permisos de administrador para acceder a esta página', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def index():
    # Get solicitudes statistics
    total_solicitudes = SolicitudEquivalencia.query.count()
    solicitudes_pendientes = SolicitudEquivalencia.query.filter_by(estado='en_evaluacion').count()
    solicitudes_aprobadas = SolicitudEquivalencia.query.filter_by(estado='aprobada').count()
    solicitudes_rechazadas = SolicitudEquivalencia.query.filter_by(estado='rechazada').count()
    
    return render_template('admin/index.html',
                           total_solicitudes=total_solicitudes,
                           solicitudes_pendientes=solicitudes_pendientes,
                           solicitudes_aprobadas=solicitudes_aprobadas,
                           solicitudes_rechazadas=solicitudes_rechazadas)

@admin_bp.route('/usuarios', methods=['GET'])
@login_required
@admin_required
def list_usuarios():
    """View all users in the system (read-only, managed via Keycloak)"""
    usuarios = Usuario.query.all()
    evaluador_service = EvaluadorService()
    stats = evaluador_service.get_evaluadores_stats()
    
    # Add message about Keycloak management
    flash('Los usuarios se gestionan exclusivamente a través de Keycloak. Esta vista es solo informativa. Use "Gestión de Evaluadores" para sincronizar usuarios desde Keycloak.', 'info')
    
    return render_template('admin/list_usuarios.html', usuarios=usuarios, readonly=True, stats=stats)

# USER MANAGEMENT IS HANDLED BY KEYCLOAK - THESE ROUTES ARE DISABLED
# Users should be created and managed in Keycloak, not in this application

# @admin_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
# @login_required
# @admin_required
# def new_usuario():
#     # This functionality is now handled by Keycloak
#     flash('La creación de usuarios se maneja exclusivamente a través de Keycloak', 'warning')
#     return redirect(url_for('admin.list_usuarios'))

# @admin_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
# @login_required
# @admin_required
# def edit_usuario(id):
#     # This functionality is now handled by Keycloak
#     flash('La edición de usuarios se maneja exclusivamente a través de Keycloak', 'warning')
#     return redirect(url_for('admin.list_usuarios'))

# @admin_bp.route('/usuarios/eliminar/<int:id>')
# @login_required
# @admin_required  
# def delete_usuario(id):
#     # This functionality is now handled by Keycloak
#     flash('La eliminación de usuarios se maneja exclusivamente a través de Keycloak', 'warning')
#     return redirect(url_for('admin.list_usuarios'))

@admin_bp.route('/evaluadores')
@login_required
@admin_required
def list_evaluadores():
    """List all evaluadores from Keycloak with their workload information"""
    evaluador_service = EvaluadorService()
    
    # Ensure fresh data from Keycloak
    evaluadores_with_workload = evaluador_service.get_evaluadores_for_selection()
    stats = evaluador_service.get_evaluadores_stats()
    
    # Add info message about data source
    if evaluador_service.is_keycloak_enabled():
        flash(f'Mostrando {len(evaluadores_with_workload)} evaluadores sincronizados desde Keycloak.', 'info')
    else:
        flash('Keycloak no está configurado. Mostrando evaluadores locales únicamente.', 'warning')
    
    return render_template('admin/list_evaluadores.html', 
                         evaluadores_with_workload=evaluadores_with_workload,
                         stats=stats)

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_solicitudes = SolicitudEquivalencia.query.count()
    solicitudes_pendientes = SolicitudEquivalencia.query.filter_by(estado='pendiente').count()
    solicitudes_aprobadas = SolicitudEquivalencia.query.filter_by(estado='aprobada').count()
    solicitudes_rechazadas = SolicitudEquivalencia.query.filter_by(estado='rechazada').count()
    
    usuarios_evaluadores = Usuario.query.filter_by(rol='evaluador').count()
    usuarios_depto = Usuario.query.filter_by(rol='depto_estudiantes').count()
    
    return render_template('admin/dashboard.html',
                           total_solicitudes=total_solicitudes,
                           solicitudes_pendientes=solicitudes_pendientes,
                           solicitudes_aprobadas=solicitudes_aprobadas,
                           solicitudes_rechazadas=solicitudes_rechazadas,
                           usuarios_evaluadores=usuarios_evaluadores,
                           usuarios_depto=usuarios_depto)

@admin_bp.route('/debug/google-drive', methods=['GET'])
@login_required
@admin_required
def debug_google_drive():
    """Ruta de debug para probar la conexión con Google Drive"""
    try:
        drive_service = GoogleDriveService()
        
        # Verificar configuración
        config_result = drive_service.verificar_configuracion()
        if not config_result['success']:
            return jsonify({
                'success': False,
                'error': 'Configuración incompleta',
                'missing_config': config_result['missing_config']
            })
        
        # Intentar crear una carpeta de prueba
        test_result = drive_service.crear_carpeta_equivalencia(
            dni='12345678',
            carrera_origen='Ingeniería de Prueba',
            id_equivalencia='TEST-001',
        )
        
        return jsonify({
            'success': True,
            'config_check': config_result,
            'test_folder_creation': test_result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error en debug: {str(e)}'
        })

@admin_bp.route('/manage_evaluadores')
@login_required
@admin_required
def manage_evaluadores():
    """Admin view for managing evaluator assignments and workload"""
    evaluador_service = EvaluadorService()
    
    # Ensure we have fresh evaluador data from Keycloak
    evaluadores_with_workload = evaluador_service.get_evaluadores_for_selection()
    
    # Get all solicitudes with their evaluator assignments
    solicitudes = SolicitudEquivalencia.query.all()
    
    # Get unassigned solicitudes
    unassigned_solicitudes = SolicitudEquivalencia.query.filter(
        SolicitudEquivalencia.evaluador_id.is_(None),
        SolicitudEquivalencia.estado.in_(['pendiente', 'en_evaluacion'])
    ).all()
    
    # Add info flash if Keycloak is enabled
    if evaluador_service.is_keycloak_enabled():
        flash('Los evaluadores se sincronizan automáticamente desde Keycloak. Lista actualizada.', 'info')
    
    return render_template('admin/manage_evaluadores.html', 
                         evaluadores_with_workload=evaluadores_with_workload,
                         unassigned_solicitudes=unassigned_solicitudes,
                         all_solicitudes=solicitudes)

@admin_bp.route('/assign_evaluador', methods=['POST'])
@login_required
@admin_required
def assign_evaluador():
    """Admin endpoint to assign evaluator to solicitud"""
    evaluador_service = EvaluadorService()
    solicitud_id = request.form.get('solicitud_id')
    evaluador_id = request.form.get('evaluador_id')
    
    if not solicitud_id:
        flash('ID de solicitud requerido', 'danger')
        return redirect(url_for('admin.manage_evaluadores'))
    
    if evaluador_id:
        success, message = evaluador_service.assign_evaluador_to_solicitud(solicitud_id, evaluador_id)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    else:
        success, message = evaluador_service.unassign_evaluador_from_solicitud(solicitud_id)
        if success:
            flash(message, 'info')
        else:
            flash(message, 'danger')
    
    return redirect(url_for('admin.manage_evaluadores'))

@admin_bp.route('/sync_evaluadores', methods=['POST'])
@login_required
@admin_required 
def sync_evaluadores():
    """Admin endpoint to sync evaluadores from Keycloak"""
    evaluador_service = EvaluadorService()
    
    if evaluador_service.is_keycloak_enabled():
        try:
            force_sync = request.form.get('force') == 'true'
            if force_sync:
                evaluadores = evaluador_service.force_sync_evaluadores()
                flash(f'Sincronización forzada completada: {len(evaluadores)} evaluadores', 'success')
            else:
                evaluadores = evaluador_service.keycloak_service.sync_all_evaluadores()
                flash(f'Sincronizados {len(evaluadores)} evaluadores desde Keycloak', 'success')
        except Exception as e:
            flash(f'Error al sincronizar evaluadores: {str(e)}', 'danger')
    else:
        flash('Keycloak no está habilitado', 'warning')
    
    return redirect(url_for('admin.manage_evaluadores'))

@admin_bp.route('/refresh_evaluadores', methods=['POST'])
@login_required
@admin_required
def refresh_evaluadores():
    """Manually refresh evaluadores from Keycloak"""
    evaluador_service = EvaluadorService()
    
    if evaluador_service.is_keycloak_enabled():
        try:
            # Force refresh from Keycloak
            evaluadores = evaluador_service.ensure_fresh_evaluadores()
            flash(f'Lista de evaluadores actualizada: {len(evaluadores)} evaluadores disponibles desde Keycloak.', 'success')
        except Exception as e:
            flash(f'Error al actualizar evaluadores desde Keycloak: {str(e)}', 'danger')
    else:
        flash('Keycloak no está configurado. No se puede actualizar desde el servidor de autenticación.', 'warning')
    
    # Redirect back to the referring page or default to manage_evaluadores
    return redirect(request.referrer or url_for('admin.manage_evaluadores'))
