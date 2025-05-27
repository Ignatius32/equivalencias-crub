import requests
import json
import os
from datetime import datetime
from flask import current_app

class GoogleDriveService:
    """Servicio para interactuar con Google Drive a través de Google Apps Script"""
    
    def __init__(self):
        self.gas_url = os.getenv('GOOGLE_APPS_SCRIPT_URL')
        self.secure_token = os.getenv('GOOGLE_DRIVE_SECURE_TOKEN')
        self.folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        self.dictamen_template_id = os.getenv('DICTAMEN_TEMPLATE_ID')
    def _make_request(self, action, data):
        """Hace una petición al Google Apps Script"""
        try:
            payload = {
                'action': action,
                'token': self.secure_token,
                **data
            }
            
            current_app.logger.info(f"Enviando petición a Google Apps Script: {action}")
            current_app.logger.debug(f"URL: {self.gas_url}")
            current_app.logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                self.gas_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            current_app.logger.info(f"Respuesta HTTP: {response.status_code}")
            current_app.logger.debug(f"Contenido respuesta: {response.text}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        current_app.logger.info(f"Petición exitosa: {result.get('message', 'Sin mensaje')}")
                        return result
                    else:
                        error_msg = result.get('message', 'Error desconocido')
                        current_app.logger.error(f"Error en Google Apps Script: {error_msg}")
                        return {'success': False, 'error': error_msg}
                except json.JSONDecodeError as e:
                    current_app.logger.error(f"Error al decodificar JSON: {e}")
                    current_app.logger.error(f"Respuesta recibida: {response.text}")
                    return {'success': False, 'error': 'Respuesta inválida del servidor'}
            else:
                current_app.logger.error(f"Error HTTP {response.status_code}: {response.text}")
                return {'success': False, 'error': f'Error HTTP {response.status_code}'}
                
        except requests.exceptions.Timeout:
            current_app.logger.error("Timeout al conectar con Google Apps Script")
            return {'success': False, 'error': 'Timeout de conexión'}
        except requests.exceptions.ConnectionError:
            current_app.logger.error("Error de conexión con Google Apps Script")
            return {'success': False, 'error': 'Error de conexión'}
        except Exception as e:
            current_app.logger.error(f"Error al hacer petición a Google Apps Script: {str(e)}")
            return {'success': False, 'error': f'Error inesperado: {str(e)}'}
    def crear_carpeta_equivalencia(self, dni, carrera_origen, id_equivalencia, timestamp=None):
        """
        Crea una carpeta en Google Drive para una equivalencia específica
        
        Args:
            dni (str): DNI del solicitante
            carrera_origen (str): Carrera de origen del solicitante
            id_equivalencia (str): ID de la equivalencia
            timestamp (datetime, optional): Timestamp. Si no se proporciona, usa datetime.now()
        
        Returns:
            dict: Resultado de la operación con folder_id si es exitosa
        """
        # Verificar configuración primero
        config_check = self.verificar_configuracion()
        if not config_check['success']:
            error_msg = f"Configuración incompleta: {', '.join(config_check['missing_config'])}"
            current_app.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        if not timestamp:
            timestamp = datetime.now()
        
        # Sanitizar nombre de la carpeta
        carrera_sanitizada = self._sanitize_folder_name(carrera_origen)
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
        folder_name = f"{dni}_{carrera_sanitizada}_{id_equivalencia}_{timestamp_str}"
        
        current_app.logger.info(f"Creando carpeta en Google Drive: {folder_name}")
        current_app.logger.info(f"Carpeta padre ID: {self.folder_id}")
        
        data = {
            'parentFolderId': self.folder_id,
            'folderName': folder_name
        }
        
        result = self._make_request('createNestedFolder', data)
        if result and result.get('success'):
            folder_id = result.get('folderId')
            current_app.logger.info(f"Carpeta creada exitosamente: {folder_id}")
            return {
                'success': True,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'folder_url': f"https://drive.google.com/drive/folders/{folder_id}"
            }
        else:
            error_msg = result.get('error', 'Error desconocido') if result else 'Sin respuesta del servidor'
            current_app.logger.error(f"Error al crear carpeta: {error_msg}")
            return {
                'success': False,
                'error': f'No se pudo crear la carpeta en Google Drive: {error_msg}'
            }
    
    def eliminar_archivo(self, file_id):
        """
        Elimina un archivo de Google Drive
        
        Args:
            file_id (str): ID del archivo a eliminar
            
        Returns:
            dict: Resultado de la operación
        """
        current_app.logger.info(f"Eliminando archivo de Google Drive: {file_id}")
        
        data = {
            'fileId': file_id
        }
        
        result = self._make_request('deleteFile', data)
        if result:
            current_app.logger.info(f"Archivo eliminado exitosamente: {file_id}")
            return {'success': True}
        else:
            current_app.logger.error(f"Error al eliminar archivo: {file_id}")
            return {
                'success': False,
                'error': 'No se pudo eliminar el archivo de Google Drive'
            }
    
    def eliminar_carpeta(self, folder_id):
        """
        Elimina una carpeta de Google Drive
        
        Args:
            folder_id (str): ID de la carpeta a eliminar
            
        Returns:
            dict: Resultado de la operación
        """
        current_app.logger.info(f"Eliminando carpeta de Google Drive: {folder_id}")
        
        data = {
            'folderId': folder_id
        }
        
        result = self._make_request('deleteFolder', data)
        if result:
            current_app.logger.info(f"Carpeta eliminada exitosamente: {folder_id}")
            return {'success': True}
        else:
            current_app.logger.error(f"Error al eliminar carpeta: {folder_id}")
            return {
                'success': False,
                'error': 'No se pudo eliminar la carpeta de Google Drive'
            }
    
    def subir_archivo(self, folder_id, file_path, file_name):
        """
        Sube un archivo a una carpeta específica en Google Drive
        
        Args:
            folder_id (str): ID de la carpeta destino
            file_path (str): Ruta local del archivo
            file_name (str): Nombre del archivo
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()
            
            # Convertir a base64 para envío
            import base64
            file_data_b64 = base64.b64encode(file_data).decode('utf-8')
            
            # Determinar tipo MIME
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            data = {
                'folderId': folder_id,
                'fileName': file_name,
                'fileData': file_data_b64,
                'mimeType': mime_type
            }
            
            result = self._make_request('uploadFile', data)
            if result:
                return {
                    'success': True,
                    'file_id': result.get('fileId'),
                    'file_url': f"https://drive.google.com/file/d/{result.get('fileId')}/view"
                }
            else:
                return {
                    'success': False,
                    'error': 'No se pudo subir el archivo a Google Drive'
                }
                
        except Exception as e:
            current_app.logger.error(f"Error al subir archivo: {str(e)}")
            return {
                'success': False,
                'error': f'Error al procesar el archivo: {str(e)}'
            }
    
    def _sanitize_folder_name(self, name):
        """
        Sanitiza el nombre de una carpeta removiendo caracteres especiales
        
        Args:
            name (str): Nombre original
            
        Returns:
            str: Nombre sanitizado
        """
        # Normalizar caracteres acentuados
        import unicodedata
        normalized = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('ascii')
        
        # Reemplazar caracteres no válidos con guión bajo
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', normalized)
        
        # Remover guiones bajos múltiples y al inicio/final
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')
        
        return sanitized
    
    def generar_nombre_archivo_solicitud(self, dni, carrera_origen, id_equivalencia, extension):
        """
        Genera el nombre del archivo de solicitud según el formato especificado
        
        Args:
            dni (str): DNI del solicitante
            carrera_origen (str): Carrera de origen
            id_equivalencia (str): ID de la equivalencia
            extension (str): Extensión del archivo (incluye el punto)
        
        Returns:
            str: Nombre del archivo sanitizado
        """
        carrera_sanitizada = self._sanitize_folder_name(carrera_origen)
        nombre_archivo = f"solicitud_equivalencia_{dni}_{carrera_sanitizada}_{id_equivalencia}{extension}"
        return nombre_archivo
    
    def verificar_configuracion(self):
        """
        Verifica que la configuración de Google Drive esté completa
        
        Returns:
            dict: Estado de la configuración
        """
        missing = []
        
        if not self.gas_url:
            missing.append('GOOGLE_APPS_SCRIPT_URL')
        if not self.secure_token:
            missing.append('GOOGLE_DRIVE_SECURE_TOKEN')
        if not self.folder_id:
            missing.append('GOOGLE_DRIVE_FOLDER_ID')
        if not self.dictamen_template_id:
            missing.append('DICTAMEN_TEMPLATE_ID')
        
        if missing:
            return {
                'success': False,
                'missing_config': missing
            }
        
        return {'success': True}

    def crear_dictamen_final(self, solicitud, placeholders):
        """
        Crea el dictamen final usando el template de Google Docs
        
        Args:
            solicitud (SolicitudEquivalencia): La solicitud de equivalencia
            placeholders (dict): Diccionario con los placeholders y sus valores
            
        Returns:
            dict: Resultado de la operación con file_id si es exitosa
        """
        current_app.logger.info(f"Creando dictamen final para solicitud {solicitud.id_solicitud}")
        
        # Verificar configuración
        config_check = self.verificar_configuracion()
        if not config_check['success']:
            error_msg = f"Configuración incompleta: {', '.join(config_check['missing_config'])}"
            current_app.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        if not self.dictamen_template_id:
            error_msg = "DICTAMEN_TEMPLATE_ID no configurado"
            current_app.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # Generar nombre del documento
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        doc_name = f"Dictamen_Final_{solicitud.dni_solicitante}_{solicitud.id_solicitud}_{timestamp}"
        data = {
            'templateId': self.dictamen_template_id,
            'newFileName': doc_name,
            'placeholders': placeholders,
            'folderId': solicitud.google_drive_folder_id
        }
        
        current_app.logger.info(f"Enviando datos para crear dictamen: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        result = self._make_request('copyDocumentFromTemplate', data)
        if result and result.get('success'):
            file_id = result.get('fileId')
            file_url = result.get('fileUrl')
            current_app.logger.info(f"Dictamen final creado exitosamente: {file_id}")
            return {
                'success': True,
                'file_id': file_id,
                'file_url': file_url,
                'file_name': doc_name
            }
        else:
            error_msg = result.get('message', 'Error desconocido') if result else 'Sin respuesta del servidor'
            current_app.logger.error(f"Error al crear dictamen final: {error_msg}")
            return {
                'success': False,
                'error': f'No se pudo crear el dictamen final: {error_msg}'
            }
    
    def actualizar_dictamen_final(self, file_id, placeholders):
        """
        Actualiza un dictamen final existente con nuevos placeholders
        
        Args:
            file_id (str): ID del documento de Google Docs
            placeholders (dict): Diccionario con los placeholders y sus valores
            
        Returns:
            dict: Resultado de la operación
        """
        current_app.logger.info(f"Actualizando dictamen final: {file_id}")
        
        data = {
            'documentId': file_id,
            'placeholders': placeholders
        }
        
        result = self._make_request('updateDocumentPlaceholders', data)
        if result and result.get('success'):
            current_app.logger.info(f"Dictamen final actualizado exitosamente: {file_id}")
            return {'success': True}
        else:
            error_msg = result.get('message', 'Error desconocido') if result else 'Sin respuesta del servidor'
            current_app.logger.error(f"Error al actualizar dictamen final: {error_msg}")
            return {
                'success': False,
                'error': f'No se pudo actualizar el dictamen final: {error_msg}'
            }
