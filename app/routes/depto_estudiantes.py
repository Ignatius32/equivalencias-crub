from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import SolicitudEquivalencia, Usuario, Dictamen
from app import db
from app.services.google_drive_service import GoogleDriveService
from app.services.dictamen_service import DictamenService
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
        # Guardar el estado anterior antes de modificar la solicitud
        estado_anterior = solicitud.estado
        nuevo_estado = request.form.get('estado')
        
        solicitud.nombre_solicitante = request.form.get('nombre')
        solicitud.apellido_solicitante = request.form.get('apellido')
        solicitud.dni_solicitante = request.form.get('dni')
        solicitud.legajo_crub = request.form.get('legajo_crub')
        solicitud.correo_solicitante = request.form.get('correo')
        solicitud.institucion_origen = request.form.get('institucion_origen')    
        solicitud.carrera_origen = request.form.get('carrera_origen')
        solicitud.carrera_crub_destino = request.form.get('carrera_crub_destino')
        solicitud.observaciones_solicitante = request.form.get('observaciones')
        
        # Manejar las asignaturas (dictámenes)
        
        # Si el estado cambia de 'aprobada'/'rechazada' a 'en_evaluacion', 
        # preservar los dictámenes que ya tienen evaluaciones
        if (estado_anterior in ['aprobada', 'rechazada'] and 
            nuevo_estado == 'en_evaluacion'):
            
            # Solo actualizar las asignaturas origen/destino, preservando las evaluaciones
            asignaturas_origen = request.form.getlist('asignatura_origen[]')
            asignaturas_destino = request.form.getlist('asignatura_destino[]')
            
            # Crear un diccionario de los dictámenes existentes por índice
            dictamenes_existentes = list(solicitud.dictamenes)
            
            # Actualizar dictámenes existentes
            for i, (origen, destino) in enumerate(zip(asignaturas_origen, asignaturas_destino)):
                if origen.strip() and destino.strip():
                    if i < len(dictamenes_existentes):
                        # Actualizar dictamen existente preservando la evaluación
                        dictamen = dictamenes_existentes[i]
                        dictamen.asignatura_origen = origen
                        dictamen.asignatura_destino = destino
                        # NO tocar tipo_equivalencia, observaciones, evaluador_id, fecha_dictamen
                    else:
                        # Crear nuevo dictamen si hay más asignaturas que dictámenes existentes
                        dictamen = Dictamen(
                            asignatura_origen=origen,
                            asignatura_destino=destino,
                            tipo_equivalencia=None,
                            observaciones=None,
                            solicitud_id=solicitud.id
                        )
                        db.session.add(dictamen)
            
            # Eliminar dictámenes sobrantes si hay menos asignaturas que dictámenes
            pares_validos = sum(1 for origen, destino in zip(asignaturas_origen, asignaturas_destino) 
                              if origen.strip() and destino.strip())
            if pares_validos < len(dictamenes_existentes):
                for dictamen in dictamenes_existentes[pares_validos:]:
                    db.session.delete(dictamen)
                    
        else:
            # Comportamiento normal: eliminar todos los dictámenes y recrear
            for dictamen in solicitud.dictamenes:
                db.session.delete(dictamen)
                
            # Luego, crear los nuevos dictámenes si existen
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
        
        # Actualizar evaluador
        evaluador_id = request.form.get('evaluador_id')
        if evaluador_id:
            solicitud.evaluador_id = evaluador_id

        # Manejar archivos adjuntos si se sube uno nuevo
        if 'archivo_solicitud' in request.files:
            archivo = request.files['archivo_solicitud']
            if archivo.filename:
                current_app.logger.info(f"Reemplazando archivo para solicitud {solicitud.id_solicitud}")
                # 1. Eliminar archivo anterior del sistema de archivos local si existe
                if solicitud.ruta_archivo:
                    ruta_anterior = os.path.join(current_app.root_path, 'static', solicitud.ruta_archivo)
                    if os.path.exists(ruta_anterior):
                        try:
                            os.remove(ruta_anterior)
                            current_app.logger.info(f"Archivo local anterior eliminado: {ruta_anterior}")
                        except Exception as e:
                            current_app.logger.error(f"Error al eliminar archivo local anterior: {str(e)}")
                # 2. Eliminar archivo anterior de Google Drive si existe
                if solicitud.google_drive_file_id and solicitud.google_drive_folder_id:
                    try:
                        drive_service = GoogleDriveService()
                        config_check = drive_service.verificar_configuracion()
                        if config_check['success']:
                            delete_result = drive_service.eliminar_archivo(solicitud.google_drive_file_id)
                            if delete_result['success']:
                                current_app.logger.info(f"Archivo anterior eliminado de Google Drive: {solicitud.google_drive_file_id}")
                                solicitud.google_drive_file_id = None
                            else:
                                current_app.logger.warning(f"No se pudo eliminar archivo anterior de Google Drive: {delete_result.get('error')}")
                    except Exception as e:
                        current_app.logger.error(f"Error al eliminar archivo anterior de Google Drive: {str(e)}")
                # 3. Generar nuevo ID único para el archivo
                archivo_id = str(uuid.uuid4())
                solicitud.id_archivo_solicitud = archivo_id
                # 4. Guardar el nuevo archivo localmente
                extension = os.path.splitext(archivo.filename)[1]
                nombre_archivo = f"{archivo_id}{extension}"
                ruta_archivo = os.path.join(current_app.root_path, 'static/uploads', nombre_archivo)
                os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
                archivo.save(ruta_archivo)
                solicitud.ruta_archivo = f"uploads/{nombre_archivo}"
                current_app.logger.info(f"Nuevo archivo guardado localmente: {ruta_archivo}")
                # 5. Subir nuevo archivo a Google Drive si la carpeta existe
                if solicitud.google_drive_folder_id:
                    try:
                        drive_service = GoogleDriveService()
                        config_check = drive_service.verificar_configuracion()
                        if config_check['success']:
                            nombre_archivo_drive = drive_service.generar_nombre_archivo_solicitud(
                                dni=solicitud.dni_solicitante,
                                carrera_origen=solicitud.carrera_origen,
                                id_equivalencia=solicitud.id_solicitud,
                                extension=extension
                            )
                            upload_result = drive_service.subir_archivo(
                                folder_id=solicitud.google_drive_folder_id,
                                file_path=ruta_archivo,
                                file_name=nombre_archivo_drive
                            )
                            if upload_result['success']:
                                solicitud.google_drive_file_id = upload_result['file_id']
                                current_app.logger.info(f"Nuevo archivo subido a Google Drive: {upload_result['file_url']}")
                                flash('Archivo reemplazado exitosamente en Google Drive', 'success')
                            else:
                                current_app.logger.error(f"Error al subir nuevo archivo a Google Drive: {upload_result.get('error')}")
                                flash('Archivo guardado localmente, pero hubo un error al subirlo a Google Drive', 'warning')
                        else:
                            current_app.logger.warning("Google Drive no configurado correctamente")
                            flash('Archivo guardado localmente, pero Google Drive no está disponible', 'warning')
                    except Exception as e:
                        current_app.logger.error(f"Error al subir archivo a Google Drive: {str(e)}")
                        flash('Archivo guardado localmente, pero hubo un error con Google Drive', 'warning')
                else:
                    current_app.logger.warning("No hay carpeta de Google Drive asociada a esta solicitud")
                    flash('Archivo actualizado localmente', 'success')

        # Manejar documentación complementaria si se sube una nueva
        if 'doc_complementaria' in request.files:
            doc_complementaria = request.files['doc_complementaria']
            if doc_complementaria.filename:
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
          # Asignar el nuevo estado al final del proceso
        if nuevo_estado != estado_anterior:
            solicitud.estado = nuevo_estado
            
            # Manejar cambios de estado y dictamen final
            dictamen_service = DictamenService()
            dictamen_result = dictamen_service.manejar_cambio_estado(solicitud, estado_anterior, nuevo_estado)
            
            if not dictamen_result['success']:
                flash(f'Error al procesar dictamen: {dictamen_result["error"]}', 'warning')
            else:
                if dictamen_result['message'] != 'No se requiere acción para el dictamen final':
                    flash(dictamen_result['message'], 'info')
        else:
            solicitud.estado = nuevo_estado
        
        db.session.commit()
        flash('Solicitud de equivalencia actualizada correctamente', 'success')
        return redirect(url_for('depto.list_equivalencias'))
    
    return render_template('depto_estudiantes/edit_equivalencia.html', solicitud=solicitud, evaluadores=evaluadores)

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
