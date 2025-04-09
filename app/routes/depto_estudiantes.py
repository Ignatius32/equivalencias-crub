from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import SolicitudEquivalencia, Usuario, Dictamen
from app import db
from functools import wraps
import os
from datetime import datetime
import uuid

depto_bp = Blueprint('depto', __name__, url_prefix='/depto_estudiantes')

# Decorador para verificar si el usuario es del departamento de estudiantes
def depto_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'depto_estudiantes':
            if current_user.rol == 'admin':
                # El administrador también puede acceder a estas rutas
                return f(*args, **kwargs)
            flash('Se requieren permisos del Departamento de Estudiantes para acceder a esta página', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@depto_bp.route('/')
@login_required
@depto_required
def index():
    return redirect(url_for('depto.list_equivalencias'))

@depto_bp.route('/equivalencias')
@login_required
@depto_required
def list_equivalencias():
    solicitudes = SolicitudEquivalencia.query.all()
    return render_template('depto_estudiantes/list_equivalencias.html', solicitudes=solicitudes)

@depto_bp.route('/equivalencias/nueva', methods=['GET', 'POST'])
@login_required
@depto_required
def new_equivalencia():
    evaluadores = Usuario.query.filter_by(rol='evaluador').all()
    
    if request.method == 'POST':
        # Generar ID único para la solicitud
        id_solicitud = f"EQ-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Crear solicitud de equivalencia
        solicitud = SolicitudEquivalencia(
            id_solicitud=id_solicitud,
            estado='pendiente',
            fecha_solicitud=datetime.now(),
            
            nombre_solicitante=request.form.get('nombre'),
            apellido_solicitante=request.form.get('apellido'),
            dni_solicitante=request.form.get('dni'),
            legajo_crub=request.form.get('legajo_crub'),
            correo_solicitante=request.form.get('correo'),
            institucion_origen=request.form.get('institucion_origen'),
            carrera_origen=request.form.get('carrera_origen'),
            carrera_crub_destino=request.form.get('carrera_crub_destino'),
            asignaturas_destino_solicitadas=request.form.get('asignaturas_solicitadas'),
            observaciones_solicitante=request.form.get('observaciones')
        )
        
        # Asignar evaluador si se seleccionó uno
        evaluador_id = request.form.get('evaluador_id')
        if evaluador_id:
            solicitud.evaluador_id = evaluador_id
        
        # Manejar archivos adjuntos
        if 'archivo_solicitud' in request.files:
            archivo = request.files['archivo_solicitud']
            if archivo.filename:
                # Generar nombre único para el archivo
                archivo_id = str(uuid.uuid4())
                solicitud.id_archivo_solicitud = archivo_id
                
                # Guardar el archivo
                extension = os.path.splitext(archivo.filename)[1]
                nombre_archivo = f"{archivo_id}{extension}"
                ruta_archivo = os.path.join(current_app.root_path, 'static/uploads', nombre_archivo)
                archivo.save(ruta_archivo)
                solicitud.ruta_archivo = f"uploads/{nombre_archivo}"
        
        # Guardar la solicitud en la base de datos
        db.session.add(solicitud)
        db.session.commit()
        
        # Crear dictámenes iniciales para cada asignatura solicitada
        asignaturas = [a.strip() for a in solicitud.asignaturas_destino_solicitadas.split(',')]
        for asignatura in asignaturas:
            dictamen = Dictamen(
                asignatura_origen=f"Por determinar - {asignatura}",
                asignatura_destino=asignatura,
                tipo_equivalencia=None,
                observaciones=None,
                solicitud_id=solicitud.id
            )
            db.session.add(dictamen)
        
        db.session.commit()
        flash('Solicitud de equivalencia creada correctamente', 'success')
        return redirect(url_for('depto.list_equivalencias'))
    
    return render_template('depto_estudiantes/new_equivalencia.html', evaluadores=evaluadores)

@depto_bp.route('/equivalencias/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@depto_required
def edit_equivalencia(id):
    solicitud = SolicitudEquivalencia.query.get_or_404(id)
    evaluadores = Usuario.query.filter_by(rol='evaluador').all()
    
    if request.method == 'POST':
        solicitud.nombre_solicitante = request.form.get('nombre')
        solicitud.apellido_solicitante = request.form.get('apellido')
        solicitud.dni_solicitante = request.form.get('dni')
        solicitud.legajo_crub = request.form.get('legajo_crub')
        solicitud.correo_solicitante = request.form.get('correo')
        solicitud.institucion_origen = request.form.get('institucion_origen')
        solicitud.carrera_origen = request.form.get('carrera_origen')
        solicitud.carrera_crub_destino = request.form.get('carrera_crub_destino')
        solicitud.asignaturas_destino_solicitadas = request.form.get('asignaturas_solicitadas')
        solicitud.observaciones_solicitante = request.form.get('observaciones')
        solicitud.estado = request.form.get('estado')
        
        # Actualizar evaluador
        evaluador_id = request.form.get('evaluador_id')
        if evaluador_id:
            solicitud.evaluador_id = evaluador_id
        
        # Manejar archivos adjuntos si se sube uno nuevo
        if 'archivo_solicitud' in request.files:
            archivo = request.files['archivo_solicitud']
            if archivo.filename:
                # Eliminar archivo anterior si existe
                if solicitud.ruta_archivo:
                    ruta_anterior = os.path.join(current_app.root_path, 'static', solicitud.ruta_archivo)
                    if os.path.exists(ruta_anterior):
                        os.remove(ruta_anterior)
                
                # Generar nombre único para el nuevo archivo
                archivo_id = str(uuid.uuid4())
                solicitud.id_archivo_solicitud = archivo_id
                
                # Guardar el archivo
                extension = os.path.splitext(archivo.filename)[1]
                nombre_archivo = f"{archivo_id}{extension}"
                ruta_archivo = os.path.join(current_app.root_path, 'static/uploads', nombre_archivo)
                archivo.save(ruta_archivo)
                solicitud.ruta_archivo = f"uploads/{nombre_archivo}"
        
        db.session.commit()
        flash('Solicitud de equivalencia actualizada correctamente', 'success')
        return redirect(url_for('depto.list_equivalencias'))
    
    return render_template('depto_estudiantes/edit_equivalencia.html', solicitud=solicitud, evaluadores=evaluadores)

@depto_bp.route('/equivalencias/eliminar/<int:id>')
@login_required
@depto_required
def delete_equivalencia(id):
    solicitud = SolicitudEquivalencia.query.get_or_404(id)
    
    # Eliminar archivo asociado si existe
    if solicitud.ruta_archivo:
        ruta_archivo = os.path.join(current_app.root_path, 'static', solicitud.ruta_archivo)
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
    
    # Eliminar todos los dictámenes asociados
    for dictamen in solicitud.dictamenes:
        db.session.delete(dictamen)
    
    # Eliminar la solicitud
    db.session.delete(solicitud)
    db.session.commit()
    
    flash('Solicitud de equivalencia eliminada correctamente', 'success')
    return redirect(url_for('depto.list_equivalencias'))

@depto_bp.route('/evaluadores')
@login_required
@depto_required
def manage_evaluadores():
    evaluadores = Usuario.query.filter_by(rol='evaluador').all()
    return render_template('depto_estudiantes/manage_evaluadores.html', evaluadores=evaluadores)

@depto_bp.route('/asignar_evaluador/<int:solicitud_id>', methods=['POST'])
@login_required
@depto_required
def asignar_evaluador(solicitud_id):
    solicitud = SolicitudEquivalencia.query.get_or_404(solicitud_id)
    evaluador_id = request.form.get('evaluador_id')
    
    if evaluador_id:
        evaluador = Usuario.query.filter_by(id=evaluador_id, rol='evaluador').first()
        if evaluador:
            solicitud.evaluador_id = evaluador.id
            db.session.commit()
            flash(f'Evaluador {evaluador.nombre} {evaluador.apellido} asignado correctamente', 'success')
        else:
            flash('Evaluador no encontrado', 'danger')
    else:
        solicitud.evaluador_id = None
        db.session.commit()
        flash('Solicitud sin evaluador asignado', 'info')
    
    return redirect(url_for('depto.list_equivalencias'))
