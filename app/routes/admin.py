from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Usuario, SolicitudEquivalencia
from app import db
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
    return render_template('admin/index.html')

@admin_bp.route('/usuarios', methods=['GET'])
@login_required
@admin_required
def list_usuarios():
    usuarios = Usuario.query.all()
    return render_template('admin/list_usuarios.html', usuarios=usuarios)

@admin_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def new_usuario():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        telefono = request.form.get('telefono')
        rol = request.form.get('rol')
        password = request.form.get('password')
        
        # Campos específicos para evaluadores
        legajo_evaluador = request.form.get('legajo_evaluador') if rol == 'evaluador' else None
        departamento_academico = request.form.get('departamento_academico') if rol == 'evaluador' else None
        
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(username=username).first() or Usuario.query.filter_by(email=email).first():
            flash('El nombre de usuario o email ya está en uso', 'danger')
            return render_template('admin/new_usuario.html')
            
        # Crear nuevo usuario
        usuario = Usuario(
            username=username,
            email=email,
            nombre=nombre,
            apellido=apellido,
            telefono=telefono,
            rol=rol,
            legajo_evaluador=legajo_evaluador,
            departamento_academico=departamento_academico
        )
        usuario.set_password(password)
        
        db.session.add(usuario)
        db.session.commit()
        
        flash(f'Usuario {username} creado correctamente', 'success')
        return redirect(url_for('admin.list_usuarios'))
        
    return render_template('admin/new_usuario.html')

@admin_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        usuario.username = request.form.get('username')
        usuario.email = request.form.get('email')
        usuario.nombre = request.form.get('nombre')
        usuario.apellido = request.form.get('apellido')
        usuario.telefono = request.form.get('telefono')
        usuario.rol = request.form.get('rol')
        
        # Actualizar contraseña si se proporciona una nueva
        new_password = request.form.get('password')
        if new_password:
            usuario.set_password(new_password)
            
        # Campos específicos para evaluadores
        if usuario.rol == 'evaluador':
            usuario.legajo_evaluador = request.form.get('legajo_evaluador')
            usuario.departamento_academico = request.form.get('departamento_academico')
        
        db.session.commit()
        flash('Usuario actualizado correctamente', 'success')
        return redirect(url_for('admin.list_usuarios'))
        
    return render_template('admin/edit_usuario.html', usuario=usuario)

@admin_bp.route('/usuarios/eliminar/<int:id>')
@login_required
@admin_required
def delete_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    
    if usuario.username == 'admin':
        flash('No se puede eliminar el usuario administrador', 'danger')
        return redirect(url_for('admin.list_usuarios'))
    
    db.session.delete(usuario)
    db.session.commit()
    
    flash('Usuario eliminado correctamente', 'success')
    return redirect(url_for('admin.list_usuarios'))

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
