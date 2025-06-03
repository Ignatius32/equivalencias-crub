from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import SolicitudEquivalencia, Dictamen
from app import db
from app.services.dictamen_service import DictamenService
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
        return redirect(url_for('evaluadores.list_equivalencias'))
    
    # Verificar si el evaluador puede editar la solicitud
    if current_user.rol != 'admin' and solicitud.estado != 'en_evaluacion':
        flash(f'No puede modificar esta solicitud. Estado actual: {solicitud.estado}. Solo se pueden editar solicitudes en estado "En Evaluación".', 'warning')
        return redirect(url_for('evaluadores.view_equivalencia', id=solicitud.id))# Obtener lista de evaluadores si el usuario es admin
    evaluadores = None
    if current_user.rol == 'admin':
        from app.models import Usuario
        evaluadores = Usuario.query.filter(Usuario.rol.in_(['evaluador', 'admin'])).all()
    
    if request.method == 'POST':
        # Procesar documentación complementaria
        if 'doc_complementaria' in request.files:
            doc_complementaria = request.files['doc_complementaria']
            if doc_complementaria and doc_complementaria.filename:
                import os, uuid
                # Eliminar archivo local anterior si existe
                if solicitud.doc_complementaria_url:
                    ruta_anterior = os.path.join(current_app.root_path, 'static', solicitud.doc_complementaria_url)
                    if os.path.exists(ruta_anterior):
                        try:
                            os.remove(ruta_anterior)
                        except Exception as e:
                            current_app.logger.error(f"Error al eliminar doc. complementaria local anterior: {str(e)}")
                # Eliminar archivo anterior de Google Drive si existe
                if solicitud.doc_complementaria_file_id and solicitud.google_drive_folder_id:
                    try:
                        from app.services.google_drive_service import GoogleDriveService
                        drive_service = GoogleDriveService()
                        config_check = drive_service.verificar_configuracion()
                        if config_check['success']:
                            delete_result = drive_service.eliminar_archivo(solicitud.doc_complementaria_file_id)
                            if delete_result['success']:
                                solicitud.doc_complementaria_file_id = None
                        else:
                            current_app.logger.warning("No se pudo eliminar doc. complementaria de Google Drive")
                    except Exception as e:
                        current_app.logger.error(f"Error al eliminar doc. complementaria de Google Drive: {str(e)}")
                # Guardar nuevo archivo localmente
                doc_complementaria_id = str(uuid.uuid4())
                extension = os.path.splitext(doc_complementaria.filename)[1]
                nombre_doc_complementaria = f"{doc_complementaria_id}{extension}"
                ruta_doc_complementaria = os.path.join(current_app.root_path, 'static/uploads', nombre_doc_complementaria)
                os.makedirs(os.path.dirname(ruta_doc_complementaria), exist_ok=True)
                doc_complementaria.save(ruta_doc_complementaria)
                solicitud.doc_complementaria_url = f"uploads/{nombre_doc_complementaria}"
                # Subir a Google Drive si la carpeta existe
                if solicitud.google_drive_folder_id:
                    try:
                        from app.services.google_drive_service import GoogleDriveService
                        drive_service = GoogleDriveService()
                        config_check = drive_service.verificar_configuracion()
                        if config_check['success']:
                            nombre_archivo_drive = f"DOC_COMPLEMENTARIA_{solicitud.id_solicitud}{extension}"
                            upload_result = drive_service.subir_archivo(
                                folder_id=solicitud.google_drive_folder_id,
                                file_path=ruta_doc_complementaria,
                                file_name=nombre_archivo_drive
                            )
                            if upload_result['success']:
                                solicitud.doc_complementaria_file_id = upload_result['file_id']
                                current_app.logger.info(f"Doc. complementaria subida a Google Drive: {upload_result['file_url']}")
                            else:
                                current_app.logger.error(f"Error al subir doc. complementaria a Google Drive: {upload_result.get('error')}")
                        else:
                            current_app.logger.warning("Google Drive no configurado correctamente para doc. complementaria")
                    except Exception as e:
                        current_app.logger.error(f"Error al subir doc. complementaria a Google Drive: {str(e)}")

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
            dictamen.observaciones = request.form.get(f'{prefix}_observaciones') or None
            # Si es la primera vez que se establece un tipo de equivalencia, guardar el evaluador
            if nuevo_tipo and not dictamen.evaluador_id:
                dictamen.evaluador_id = current_user.id
                dictamen.fecha_dictamen = datetime.now()
            # Si es admin, permitir cambiar el evaluador
            if current_user.rol == 'admin':
                nuevo_evaluador_id = request.form.get(f'{prefix}_evaluador_id')
                if nuevo_evaluador_id:
                    dictamen.evaluador_id = int(nuevo_evaluador_id)
        estado_anterior = solicitud.estado
        estado_nuevo = request.form.get('estado_solicitud')
        if estado_nuevo and estado_nuevo != estado_anterior:
            # Alertar si se está cerrando la solicitud (cambiando de "en_evaluacion" a otro estado)
            if (estado_anterior == 'en_evaluacion' and 
                estado_nuevo != 'en_evaluacion' and 
                current_user.rol != 'admin'):
                flash(f'Usted está cerrando la solicitud de equivalencia de {solicitud.nombre_solicitante} {solicitud.apellido_solicitante} con estado "{estado_nuevo}". Ya no podrá modificar los dictámenes.', 'warning')
            # Verificar si hay dictámenes pendientes
            dictamenes_pendientes = any(not dictamen.tipo_equivalencia for dictamen in solicitud.dictamenes)
            if estado_nuevo in ['aprobada', 'rechazada'] and dictamenes_pendientes:
                flash('No se puede aprobar o rechazar la solicitud mientras haya dictámenes pendientes', 'warning')
                return redirect(url_for('evaluadores.dictamen_equivalencia', id=solicitud.id))
            solicitud.estado = estado_nuevo
            if estado_nuevo in ['aprobada', 'rechazada']:
                solicitud.fecha_resolucion = datetime.now()
            # --- FIRMAR DIGITALMENTE ---
            if estado_nuevo != 'en_evaluacion':
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                firma = f"Firmado digitalmente por: {current_user.id} - {current_user.apellido} - {current_user.nombre} - {timestamp}"
                solicitud.firma_evaluador = firma
            # Manejar cambios de estado y dictamen final
            dictamen_service = DictamenService()
            dictamen_result = dictamen_service.manejar_cambio_estado(solicitud, estado_anterior, estado_nuevo)
            if not dictamen_result['success']:
                flash(f'Error al procesar dictamen: {dictamen_result["error"]}', 'warning')
            else:
                if dictamen_result['message'] != 'No se requiere acción para el dictamen final':
                    flash(dictamen_result['message'], 'info')
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
    
    # Verificar si el evaluador puede editar la solicitud
    if current_user.rol != 'admin' and solicitud.estado != 'en_evaluacion':
        flash(f'No puede modificar esta solicitud. Estado actual: {solicitud.estado}. Solo se pueden editar solicitudes en estado "En Evaluación".', 'warning')
        return redirect(url_for('evaluadores.view_equivalencia', id=solicitud.id))
    
    asignatura_origen = request.form.get('asignatura_origen')
    asignatura_destino = request.form.get('asignatura_destino')
    
    if asignatura_origen and asignatura_destino:
        dictamen = Dictamen(
            asignatura_origen=asignatura_origen,
            asignatura_destino=asignatura_destino,
            tipo_equivalencia=None,
            observaciones=None,
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
    
    # Verificar si el evaluador puede editar la solicitud
    if current_user.rol != 'admin' and solicitud.estado != 'en_evaluacion':
        flash(f'No puede modificar esta solicitud. Estado actual: {solicitud.estado}. Solo se pueden editar solicitudes en estado "En Evaluación".', 'warning')
        return redirect(url_for('evaluadores.view_equivalencia', id=solicitud.id))
    
    db.session.delete(dictamen)
    db.session.commit()
    
    flash('Dictamen eliminado correctamente', 'success')
    return redirect(url_for('evaluadores.dictamen_equivalencia', id=solicitud_id))
