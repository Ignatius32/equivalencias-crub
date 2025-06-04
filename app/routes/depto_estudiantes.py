from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import Usuario, SolicitudEquivalencia, Dictamen
from app import db
from app.services.google_drive_service import GoogleDriveService
from app.services.dictamen_service import DictamenService
from functools import wraps
from datetime import datetime
import uuid
import os

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
    evaluadores = Usuario.query.filter_by(rol='evaluador').all()
    from flask_login import current_user
    return render_template('depto_estudiantes/list_equivalencias.html', solicitudes=solicitudes, evaluadores=evaluadores, current_user=current_user)

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
            estado='en_evaluacion',
            fecha_solicitud=datetime.now(),
            
            nombre_solicitante=request.form.get('nombre'),
            apellido_solicitante=request.form.get('apellido'),
            dni_solicitante=request.form.get('dni'),
            legajo_crub=request.form.get('legajo_crub'),            correo_solicitante=request.form.get('correo'),
            institucion_origen=request.form.get('institucion_origen'),
            carrera_origen=request.form.get('carrera_origen'),
            carrera_crub_destino=request.form.get('carrera_crub_destino'),
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

        # Manejar documentación complementaria
        if 'doc_complementaria' in request.files:
            doc_complementaria = request.files['doc_complementaria']
            if doc_complementaria.filename:
                doc_complementaria_id = str(uuid.uuid4())
                extension = os.path.splitext(doc_complementaria.filename)[1]
                nombre_doc_complementaria = f"{doc_complementaria_id}{extension}"
                ruta_doc_complementaria = os.path.join(current_app.root_path, 'static/uploads', nombre_doc_complementaria)
                doc_complementaria.save(ruta_doc_complementaria)
                solicitud.doc_complementaria_url = f"uploads/{nombre_doc_complementaria}"
                # El file_id de Google Drive se asignará tras la subida
          # Guardar la solicitud en la base de datos
        db.session.add(solicitud)
        db.session.commit()
        
        # Crear carpeta en Google Drive
        try:
            drive_service = GoogleDriveService()
            config_check = drive_service.verificar_configuracion()
            
            if config_check['success']:
                folder_result = drive_service.crear_carpeta_equivalencia(
                    dni=solicitud.dni_solicitante,
                    carrera_origen=solicitud.carrera_origen,
                    id_equivalencia=solicitud.id_solicitud,
                    timestamp=solicitud.fecha_solicitud
                )
                if folder_result['success']:
                    # Actualizar la solicitud con la información de Google Drive
                    solicitud.google_drive_folder_id = folder_result['folder_id']
                    solicitud.google_drive_folder_name = folder_result['folder_name']
                    solicitud.google_drive_folder_url = folder_result['folder_url']
                    
                    # Si hay archivo adjunto, subirlo a Google Drive
                    if solicitud.ruta_archivo:
                        archivo_local = os.path.join(current_app.root_path, 'static', solicitud.ruta_archivo)
                        if os.path.exists(archivo_local):
                            # Generar nombre del archivo según el formato especificado
                            extension = os.path.splitext(solicitud.ruta_archivo)[1]
                            nombre_archivo_drive = drive_service.generar_nombre_archivo_solicitud(
                                dni=solicitud.dni_solicitante,
                                carrera_origen=solicitud.carrera_origen,
                                id_equivalencia=solicitud.id_solicitud,
                                extension=extension
                            )
                            
                            upload_result = drive_service.subir_archivo(
                                folder_id=folder_result['folder_id'],
                                file_path=archivo_local,
                                file_name=nombre_archivo_drive
                            )
                            if upload_result['success']:
                                solicitud.google_drive_file_id = upload_result['file_id']
                                current_app.logger.info(f"Archivo subido a Google Drive: {upload_result['file_url']}")
                            else:
                                current_app.logger.error(f"Error al subir archivo a Google Drive: {upload_result.get('error')}")
                    
                    # Subir documentación complementaria si existe
                    if solicitud.doc_complementaria_url:
                        archivo_local = os.path.join(current_app.root_path, 'static', solicitud.doc_complementaria_url)
                        if os.path.exists(archivo_local):
                            extension = os.path.splitext(solicitud.doc_complementaria_url)[1]
                            nombre_archivo_drive = f"DOC_COMPLEMENTARIA_{solicitud.id_solicitud}{extension}"
                            upload_result = drive_service.subir_archivo(
                                folder_id=folder_result['folder_id'],
                                file_path=archivo_local,
                                file_name=nombre_archivo_drive
                            )
                            if upload_result['success']:
                                solicitud.doc_complementaria_file_id = upload_result['file_id']
                                current_app.logger.info(f"Doc. complementaria subida a Google Drive: {upload_result['file_url']}")
                            else:
                                current_app.logger.error(f"Error al subir doc. complementaria a Google Drive: {upload_result.get('error')}")
                    db.session.commit()
                    flash(f'Solicitud creada correctamente. Carpeta de Google Drive: {folder_result["folder_name"]}', 'success')
                else:
                    flash('Solicitud creada, pero hubo un problema al crear la carpeta en Google Drive', 'warning')
            else:
                missing_config = ', '.join(config_check['missing_config'])
                flash(f'Solicitud creada, pero falta configuración de Google Drive: {missing_config}', 'warning')
                
        except Exception as e:
            current_app.logger.error(f"Error al crear carpeta en Google Drive: {str(e)}")
            flash('Solicitud creada, pero hubo un error con Google Drive', 'warning')
        
        # Crear dictámenes iniciales para cada par de asignaturas si existen
        asignaturas_origen = request.form.getlist('asignatura_origen[]')
        asignaturas_destino = request.form.getlist('asignatura_destino[]')
        
        # Solo crear dictámenes si se proporcionaron asignaturas
        if asignaturas_origen and asignaturas_destino:
            for origen, destino in zip(asignaturas_origen, asignaturas_destino):
                if origen.strip() and destino.strip():  # Solo crear si ambos campos tienen contenido
                    dictamen = Dictamen(
                        asignatura_origen=origen,
                        asignatura_destino=destino,
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
        # Actualizar datos básicos de la solicitud
        solicitud.nombre_solicitante = request.form.get('nombre')
        solicitud.apellido_solicitante = request.form.get('apellido')
        solicitud.dni_solicitante = request.form.get('dni')
        solicitud.legajo_crub = request.form.get('legajo_crub')
        solicitud.correo_solicitante = request.form.get('correo')
        solicitud.institucion_origen = request.form.get('institucion_origen')
        solicitud.carrera_origen = request.form.get('carrera_origen')
        solicitud.carrera_crub_destino = request.form.get('carrera_crub_destino')
        solicitud.observaciones_solicitante = request.form.get('observaciones')
        
        # Manejar cambio de estado
        estado_nuevo = request.form.get('estado')
        if estado_nuevo and estado_nuevo != solicitud.estado:
            solicitud.estado = estado_nuevo
            if estado_nuevo in ['aprobada', 'rechazada']:
                solicitud.fecha_resolucion = datetime.now()
        
        # Manejar cambio de evaluador
        evaluador_id = request.form.get('evaluador_id')
        if evaluador_id:
            solicitud.evaluador_id = int(evaluador_id)
        
        # Manejar archivo de solicitud
        if 'archivo_solicitud' in request.files:
            archivo = request.files['archivo_solicitud']
            if archivo and archivo.filename:
                try:
                    # Si hay un archivo existente en Google Drive, eliminarlo
                    if solicitud.google_drive_file_id:
                        try:
                            drive_service = GoogleDriveService()
                            drive_service.eliminar_archivo(solicitud.google_drive_file_id)
                        except Exception as e:
                            current_app.logger.error(f"Error al eliminar archivo existente: {str(e)}")
                    
                    # Generar nombre único para el archivo temporal
                    import tempfile
                    temp_dir = current_app.config['UPLOAD_FOLDER']
                    _, extension = os.path.splitext(archivo.filename)
                    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix=extension)
                    
                    # Guardar archivo temporalmente
                    archivo.save(temp_file.name)
                    
                    # Subir a Google Drive
                    drive_service = GoogleDriveService()
                    nombre_archivo = drive_service.generar_nombre_archivo_solicitud(
                        solicitud.dni_solicitante,
                        solicitud.carrera_origen,
                        solicitud.id_solicitud,
                        extension
                    )
                    
                    result = drive_service.subir_archivo(
                        solicitud.google_drive_folder_id,
                        temp_file.name,
                        nombre_archivo
                    )
                    
                    # Limpiar archivo temporal
                    temp_file.close()
                    os.unlink(temp_file.name)
                    
                    if result['success']:
                        solicitud.google_drive_file_id = result['file_id']
                        flash('Archivo actualizado correctamente', 'success')
                    else:
                        flash('Error al subir el archivo a Google Drive', 'danger')
                        
                except Exception as e:
                    current_app.logger.error(f"Error al procesar archivo: {str(e)}")
                    flash(f'Error al procesar el archivo: {str(e)}', 'danger')
                    if 'temp_file' in locals():
                        try:
                            os.unlink(temp_file.name)
                        except:
                            pass

        # Manejar documentación complementaria
        if 'doc_complementaria' in request.files:
            archivo = request.files['doc_complementaria']
            if archivo and archivo.filename:
                try:
                    # Si hay un archivo existente en Google Drive, eliminarlo
                    if solicitud.doc_complementaria_file_id:
                        try:
                            drive_service = GoogleDriveService()
                            drive_service.eliminar_archivo(solicitud.doc_complementaria_file_id)
                        except Exception as e:
                            current_app.logger.error(f"Error al eliminar documentación complementaria existente: {str(e)}")
                    
                    # Generar nombre único para el archivo temporal
                    import tempfile
                    temp_dir = current_app.config['UPLOAD_FOLDER']
                    _, extension = os.path.splitext(archivo.filename)
                    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix=extension)
                    
                    # Guardar archivo temporalmente
                    archivo.save(temp_file.name)
                    
                    # Subir a Google Drive
                    drive_service = GoogleDriveService()
                    nombre_archivo = f"complementaria_{solicitud.id_solicitud}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
                    
                    result = drive_service.subir_archivo(
                        solicitud.google_drive_folder_id,
                        temp_file.name,
                        nombre_archivo
                    )
                    
                    # Limpiar archivo temporal
                    temp_file.close()
                    os.unlink(temp_file.name)
                    
                    if result['success']:
                        solicitud.doc_complementaria_file_id = result['file_id']
                        solicitud.doc_complementaria_url = result.get('webViewLink')
                        flash('Documentación complementaria actualizada correctamente', 'success')
                    else:
                        flash('Error al subir la documentación complementaria a Google Drive', 'danger')
                        
                except Exception as e:
                    current_app.logger.error(f"Error al procesar documentación complementaria: {str(e)}")
                    flash(f'Error al procesar la documentación complementaria: {str(e)}', 'danger')
                    if 'temp_file' in locals():
                        try:
                            os.unlink(temp_file.name)
                        except:
                            pass
        
        try:
            db.session.commit()
            flash('Solicitud actualizada correctamente', 'success')
            return redirect(url_for('depto.list_equivalencias'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al actualizar solicitud: {str(e)}")
            flash('Error al actualizar la solicitud', 'danger')
    
    return render_template('depto_estudiantes/edit_equivalencia.html', 
                         solicitud=solicitud, 
                         evaluadores=evaluadores)

@depto_bp.route('/equivalencias/eliminar/<int:id>')
@login_required
@depto_required
def delete_equivalencia(id):
    solicitud = SolicitudEquivalencia.query.get_or_404(id)
    
    # Eliminar carpeta de Google Drive si existe
    if solicitud.google_drive_folder_id:
        try:
            drive_service = GoogleDriveService()
            config_check = drive_service.verificar_configuracion()
            
            if config_check['success']:
                delete_result = drive_service.eliminar_carpeta(solicitud.google_drive_folder_id)
                if delete_result['success']:
                    current_app.logger.info(f"Carpeta de Google Drive eliminada: {solicitud.google_drive_folder_id}")
                else:
                    current_app.logger.warning(f"No se pudo eliminar la carpeta de Google Drive: {solicitud.google_drive_folder_id}")
        except Exception as e:
            current_app.logger.error(f"Error al eliminar carpeta de Google Drive: {str(e)}")
    
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

@depto_bp.route('/equivalencias/ver/<int:id>')
@login_required
@depto_required
def view_equivalencia(id):
    solicitud = SolicitudEquivalencia.query.get_or_404(id)
    evaluadores = Usuario.query.filter_by(rol='evaluador').all()
    return render_template('depto_estudiantes/view_equivalencia.html', 
                         solicitud=solicitud,
                         evaluadores=evaluadores)

@depto_bp.route('/equivalencias/eliminar_archivo/<int:solicitud_id>/<tipo>', methods=['POST'])
@login_required
@depto_required
def eliminar_archivo(solicitud_id, tipo):
    # Verificar permisos según el tipo de archivo
    if tipo == 'complementaria' and current_user.rol != 'admin':
        flash('No tienes permisos para eliminar documentación complementaria', 'danger')
        return redirect(url_for('depto.list_equivalencias'))
    elif tipo == 'solicitud' and current_user.rol not in ['admin', 'depto_estudiantes']:
        flash('No tienes permisos para eliminar archivos de solicitud', 'danger')
        return redirect(url_for('depto.list_equivalencias'))

    solicitud = SolicitudEquivalencia.query.get_or_404(solicitud_id)
    
    try:
        drive_service = GoogleDriveService()
        
        if tipo == 'solicitud' and solicitud.google_drive_file_id:
            # Eliminar archivo de Google Drive
            result = drive_service.eliminar_archivo(solicitud.google_drive_file_id)
            if result['success']:
                solicitud.google_drive_file_id = None
                db.session.commit()
                flash('Archivo eliminado correctamente', 'success')
            else:
                flash('Error al eliminar el archivo de Google Drive', 'danger')
                
        elif tipo == 'complementaria' and solicitud.doc_complementaria_file_id:
            # Eliminar documentación complementaria
            result = drive_service.eliminar_archivo(solicitud.doc_complementaria_file_id)
            if result['success']:
                solicitud.doc_complementaria_file_id = None
                solicitud.doc_complementaria_url = None
                db.session.commit()
                flash('Documentación complementaria eliminada correctamente', 'success')
            else:
                flash('Error al eliminar la documentación complementaria de Google Drive', 'danger')
                
    except Exception as e:
        current_app.logger.error(f"Error al eliminar archivo: {str(e)}")
        flash(f'Error al eliminar el archivo: {str(e)}', 'danger')

    return redirect(url_for('depto.edit_equivalencia', id=solicitud_id))

def limpiar_archivos_temporales():
    """Limpia los archivos temporales de la carpeta de uploads"""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    for filename in os.listdir(upload_folder):
        file_path = os.path.join(upload_folder, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            current_app.logger.error(f"Error al eliminar archivo temporal {file_path}: {str(e)}")

@depto_bp.before_request
def before_request():
    """Limpia los archivos temporales antes de cada solicitud al blueprint"""
    if not hasattr(current_app, '_archivos_limpiados'):
        limpiar_archivos_temporales()
        setattr(current_app, '_archivos_limpiados', True)
