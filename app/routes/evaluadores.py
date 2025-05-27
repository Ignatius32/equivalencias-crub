from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import SolicitudEquivalencia, Dictamen
from app import db
from functools import wraps
from datetime import datetime

evaluadores_bp = Blueprint('evaluadores', __name__, url_prefix='/evaluadores')

def evaluador_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'evaluador':
            if current_user.rol == 'admin':
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
    if current_user.rol == 'admin':
        solicitudes = SolicitudEquivalencia.query.all()
    else:
        solicitudes = SolicitudEquivalencia.query.filter_by(evaluador_id=current_user.id).all()
    return render_template('evaluadores/list_equivalencias.html', solicitudes=solicitudes)

@evaluadores_bp.route('/equivalencia/<int:id>')
@login_required
@evaluador_required
def view_equivalencia(id):
    solicitud = SolicitudEquivalencia.query.get_or_404(id)
    if current_user.rol != 'admin' and solicitud.evaluador_id != current_user.id:
        flash('No tienes permiso para acceder a esta solicitud', 'danger')
        return redirect(url_for('evaluadores.list_equivalencias'))
    return render_template('evaluadores/equivalencia.html', solicitud=solicitud)

@evaluadores_bp.route('/dictamen/<int:id>', methods=['GET', 'POST'])
@login_required
@evaluador_required
def dictamen_equivalencia(id):
    solicitud = SolicitudEquivalencia.query.get_or_404(id)
    
    if current_user.rol != 'admin' and solicitud.evaluador_id != current_user.id:
        flash('No tienes permiso para acceder a esta solicitud', 'danger')
        return redirect(url_for('evaluadores.list_equivalencias'))    # Obtener lista de evaluadores si el usuario es admin
    evaluadores = None
    if current_user.rol == 'admin':
        from app.models import Usuario
        evaluadores = Usuario.query.filter(Usuario.rol.in_(['evaluador', 'admin'])).all()
    
    if request.method == 'POST':
        # Procesar cada dictamen
        for dictamen in solicitud.dictamenes:
            prefix = f'dictamen_{dictamen.id}'
            dictamen.asignatura_origen = request.form.get(f'{prefix}_asignatura_origen')
            nuevo_tipo = request.form.get(f'{prefix}_tipo_equivalencia')
            
            if nuevo_tipo == 'sin_equivalencia':
                dictamen.asignatura_destino = None
            else:
                dictamen.asignatura_destino = request.form.get(f'{prefix}_asignatura_destino')
            
            dictamen.tipo_equivalencia = nuevo_tipo
            dictamen.observaciones = request.form.get(f'{prefix}_observaciones')
            
            # Si es la primera vez que se establece un tipo de equivalencia, guardar el evaluador
            if nuevo_tipo and not dictamen.evaluador_id:
                dictamen.evaluador_id = current_user.id
                dictamen.fecha_dictamen = datetime.now()
            
            # Si es admin, permitir cambiar el evaluador
            if current_user.rol == 'admin':
                nuevo_evaluador_id = request.form.get(f'{prefix}_evaluador_id')
                if nuevo_evaluador_id:
                    dictamen.evaluador_id = int(nuevo_evaluador_id)
          # Actualizar estado de la solicitud
        estado_nuevo = request.form.get('estado_solicitud')
        if estado_nuevo:
            # Verificar si hay dictámenes pendientes
            dictamenes_pendientes = any(not dictamen.tipo_equivalencia for dictamen in solicitud.dictamenes)
            
            if estado_nuevo in ['aprobada', 'rechazada'] and dictamenes_pendientes:
                flash('No se puede aprobar o rechazar la solicitud mientras haya dictámenes pendientes', 'warning')
                return redirect(url_for('evaluadores.dictamen_equivalencia', id=solicitud.id))
            
            solicitud.estado = estado_nuevo
            if estado_nuevo in ['aprobada', 'rechazada']:
                solicitud.fecha_resolucion = datetime.now()
        
        db.session.commit()
        flash('Dictamen actualizado correctamente', 'success')
        return redirect(url_for('evaluadores.view_equivalencia', id=solicitud.id))
    
    return render_template('evaluadores/dictamen_equivalencia.html', 
                         solicitud=solicitud,
                         evaluadores=evaluadores)

@evaluadores_bp.route('/agregar_dictamen/<int:solicitud_id>', methods=['POST'])
@login_required
@evaluador_required
def agregar_dictamen(solicitud_id):
    solicitud = SolicitudEquivalencia.query.get_or_404(solicitud_id)
    
    if current_user.rol != 'admin' and solicitud.evaluador_id != current_user.id:
        flash('No tienes permiso para acceder a esta solicitud', 'danger')
        return redirect(url_for('evaluadores.list_equivalencias'))
    
    asignatura_origen = request.form.get('asignatura_origen')
    asignatura_destino = request.form.get('asignatura_destino')
    
    if asignatura_origen and asignatura_destino:
        dictamen = Dictamen(
            asignatura_origen=asignatura_origen,
            asignatura_destino=asignatura_destino,
            tipo_equivalencia=None,
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
    dictamen = Dictamen.query.get_or_404(id)
    solicitud_id = dictamen.solicitud_id
    solicitud = SolicitudEquivalencia.query.get(solicitud_id)
    
    if current_user.rol != 'admin' and solicitud.evaluador_id != current_user.id:
        flash('No tienes permiso para eliminar este dictamen', 'danger')
        return redirect(url_for('evaluadores.list_equivalencias'))
    
    db.session.delete(dictamen)
    db.session.commit()
    
    flash('Dictamen eliminado correctamente', 'success')
    return redirect(url_for('evaluadores.dictamen_equivalencia', id=solicitud_id))
