from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import SolicitudEquivalencia, Dictamen
from app import db
from functools import wraps
from datetime import datetime

evaluadores_bp = Blueprint('evaluadores', __name__, url_prefix='/evaluadores')

# Decorador para verificar si el usuario es evaluador
def evaluador_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'evaluador':
            if current_user.rol == 'admin':
                # El administrador también puede acceder a estas rutas
                return f(*args, **kwargs)
            flash('Se requieren permisos de Evaluador para acceder a esta página', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@evaluadores_bp.route('/')
@login_required
@evaluador_required
def index():
    return redirect(url_for('evaluadores.list_equivalencias'))

@evaluadores_bp.route('/equivalencias')
@login_required
@evaluador_required
def list_equivalencias():
    # Si es admin, ver todas las solicitudes
    if current_user.rol == 'admin':
        solicitudes = SolicitudEquivalencia.query.all()
    else:
        # Si es evaluador, solo ver las solicitudes asignadas
        solicitudes = SolicitudEquivalencia.query.filter_by(evaluador_id=current_user.id).all()
    
    return render_template('evaluadores/list_equivalencias.html', solicitudes=solicitudes)

@evaluadores_bp.route('/equivalencia/<int:id>')
@login_required
@evaluador_required
def view_equivalencia(id):
    # Buscar la solicitud
    solicitud = SolicitudEquivalencia.query.get_or_404(id)
    
    # Verificar que el usuario pueda acceder a esta solicitud
    if current_user.rol != 'admin' and solicitud.evaluador_id != current_user.id:
        flash('No tienes permiso para acceder a esta solicitud', 'danger')
        return redirect(url_for('evaluadores.list_equivalencias'))
    
    return render_template('evaluadores/equivalencia.html', solicitud=solicitud)

@evaluadores_bp.route('/dictamen/<int:id>', methods=['GET', 'POST'])
@login_required
@evaluador_required
def dictamen_equivalencia(id):
    # Buscar la solicitud
    solicitud = SolicitudEquivalencia.query.get_or_404(id)
    
    # Verificar que el usuario pueda acceder a esta solicitud
    if current_user.rol != 'admin' and solicitud.evaluador_id != current_user.id:
        flash('No tienes permiso para acceder a esta solicitud', 'danger')
        return redirect(url_for('evaluadores.list_equivalencias'))
    
    if request.method == 'POST':
        # Verificar si se está rechazando la solicitud completa
        if 'rechazar_solicitud' in request.form:
            solicitud.estado = 'rechazada'
            solicitud.fecha_resolucion = datetime.now()
            db.session.commit()
            flash('La solicitud ha sido rechazada', 'warning')
            return redirect(url_for('evaluadores.list_equivalencias'))
        
        # Procesar cada dictamen
        for dictamen in solicitud.dictamenes:
            prefix = f'dictamen_{dictamen.id}'
            
            # Actualizar la asignatura de origen
            dictamen.asignatura_origen = request.form.get(f'{prefix}_asignatura_origen')
            
            # Actualizar el tipo de equivalencia
            dictamen.tipo_equivalencia = request.form.get(f'{prefix}_tipo_equivalencia')
            
            # Actualizar observaciones
            dictamen.observaciones = request.form.get(f'{prefix}_observaciones')
            
            # Si se marca como sin equivalencia, limpiar la asignatura destino
            if dictamen.tipo_equivalencia == 'sin_equivalencia':
                dictamen.asignatura_destino = None
        
        # Actualizar el estado de la solicitud
        estado_nuevo = request.form.get('estado_solicitud')
        if estado_nuevo:
            solicitud.estado = estado_nuevo
            
            # Si se aprueba o rechaza, establecer la fecha de resolución
            if estado_nuevo in ['aprobada', 'rechazada']:
                solicitud.fecha_resolucion = datetime.now()
        
        # Guardar los cambios
        db.session.commit()
        
        flash('Dictamen actualizado correctamente', 'success')
        return redirect(url_for('evaluadores.view_equivalencia', id=solicitud.id))
    
    return render_template('evaluadores/dictamen_equivalencia.html', solicitud=solicitud)

@evaluadores_bp.route('/agregar_dictamen/<int:solicitud_id>', methods=['POST'])
@login_required
@evaluador_required
def agregar_dictamen(solicitud_id):
    # Buscar la solicitud
    solicitud = SolicitudEquivalencia.query.get_or_404(solicitud_id)
    
    # Verificar que el usuario pueda acceder a esta solicitud
    if current_user.rol != 'admin' and solicitud.evaluador_id != current_user.id:
        flash('No tienes permiso para acceder a esta solicitud', 'danger')
        return redirect(url_for('evaluadores.list_equivalencias'))
    
    # Crear un nuevo dictamen
    asignatura_origen = request.form.get('asignatura_origen')
    asignatura_destino = request.form.get('asignatura_destino')
    
    if asignatura_origen and asignatura_destino:
        dictamen = Dictamen(
            asignatura_origen=asignatura_origen,
            asignatura_destino=asignatura_destino,
            tipo_equivalencia='pendiente',
            observaciones='Por evaluar',
            solicitud_id=solicitud.id
        )
        
        db.session.add(dictamen)
        db.session.commit()
        flash('Dictamen agregado correctamente', 'success')
    else:
        flash('Se requieren los nombres de ambas asignaturas', 'danger')
    
    return redirect(url_for('evaluadores.dictamen_equivalencia', id=solicitud.id))

@evaluadores_bp.route('/eliminar_dictamen/<int:id>')
@login_required
@evaluador_required
def eliminar_dictamen(id):
    # Buscar el dictamen
    dictamen = Dictamen.query.get_or_404(id)
    solicitud_id = dictamen.solicitud_id
    
    # Verificar que el usuario pueda acceder a esta solicitud
    solicitud = SolicitudEquivalencia.query.get(solicitud_id)
    if current_user.rol != 'admin' and solicitud.evaluador_id != current_user.id:
        flash('No tienes permiso para eliminar este dictamen', 'danger')
        return redirect(url_for('evaluadores.list_equivalencias'))
    
    # Eliminar el dictamen
    db.session.delete(dictamen)
    db.session.commit()
    
    flash('Dictamen eliminado correctamente', 'success')
    return redirect(url_for('evaluadores.dictamen_equivalencia', id=solicitud_id))
