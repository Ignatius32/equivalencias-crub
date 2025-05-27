# -*- coding: utf-8 -*-
from datetime import datetime
from flask import current_app
from app import db
from app.services.google_drive_service import GoogleDriveService
from app.services.placeholder_processor import PlaceholderProcessor


class DictamenService:
    """Service for managing dictamen final documents"""
    
    def __init__(self):
        self.google_drive = GoogleDriveService()
        self.placeholder_processor = PlaceholderProcessor()
    
    def generar_dictamen_final(self, solicitud):
        """
        Genera el dictamen final cuando una solicitud es aprobada o rechazada
        
        Args:
            solicitud (SolicitudEquivalencia): La solicitud de equivalencia
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            current_app.logger.info(f"Generando dictamen final para solicitud {solicitud.id_solicitud}")
            
            # Verificar que la solicitud tenga estado final
            if solicitud.estado not in ['aprobada', 'rechazada']:
                return {
                    'success': False,
                    'error': 'La solicitud debe estar aprobada o rechazada para generar el dictamen final'
                }
            
            # Verificar que tenga carpeta de Google Drive
            if not solicitud.google_drive_folder_id:
                return {
                    'success': False,
                    'error': 'La solicitud no tiene carpeta asociada en Google Drive'
                }
              # Procesar placeholders
            placeholders = self.placeholder_processor.process_solicitud_placeholders(solicitud)
            
            # Eliminar dictamen existente si hay uno
            if solicitud.dictamen_final_file_id:
                current_app.logger.info(f"Eliminando dictamen final existente: {solicitud.dictamen_final_file_id}")
                self.google_drive.eliminar_archivo(solicitud.dictamen_final_file_id)
            
            # Crear nuevo dictamen
            result = self.google_drive.crear_dictamen_final(solicitud, placeholders)
            
            if result['success']:
                # Actualizar la solicitud con la información del dictamen
                solicitud.dictamen_final_file_id = result['file_id']
                solicitud.dictamen_final_url = result['file_url']
                solicitud.fecha_resolucion = datetime.now()
                
                db.session.commit()
                
                current_app.logger.info(f"Dictamen final generado exitosamente: {result['file_id']}")
                return {
                    'success': True,
                    'file_id': result['file_id'],
                    'file_url': result['file_url'],
                    'message': 'Dictamen final generado exitosamente'
                }
            else:
                return result
                
        except Exception as e:
            current_app.logger.error(f"Error al generar dictamen final: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'error': f'Error inesperado al generar dictamen final: {str(e)}'
            }
    
    def actualizar_dictamen_final(self, solicitud):
        """
        Actualiza el dictamen final existente con información actualizada
        
        Args:
            solicitud (SolicitudEquivalencia): La solicitud de equivalencia
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            if not solicitud.dictamen_final_file_id:
                return {
                    'success': False,
                    'error': 'No existe dictamen final para actualizar'
                }
              # Procesar placeholders actualizados
            placeholders = self.placeholder_processor.process_solicitud_placeholders(solicitud)
            
            # Actualizar el documento
            result = self.google_drive.actualizar_dictamen_final(solicitud.dictamen_final_file_id, placeholders)
            
            if result['success']:
                current_app.logger.info(f"Dictamen final actualizado exitosamente: {solicitud.dictamen_final_file_id}")
                return {
                    'success': True,
                    'message': 'Dictamen final actualizado exitosamente'
                }
            else:
                return result
                
        except Exception as e:
            current_app.logger.error(f"Error al actualizar dictamen final: {str(e)}")
            return {
                'success': False,
                'error': f'Error inesperado al actualizar dictamen final: {str(e)}'
            }
    
    def eliminar_dictamen_final(self, solicitud):
        """
        Elimina el dictamen final cuando la solicitud vuelve a 'en_evaluacion'
        
        Args:
            solicitud (SolicitudEquivalencia): La solicitud de equivalencia
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            if not solicitud.dictamen_final_file_id:
                return {
                    'success': True,
                    'message': 'No hay dictamen final para eliminar'
                }
            
            current_app.logger.info(f"Eliminando dictamen final: {solicitud.dictamen_final_file_id}")
            
            # Eliminar archivo de Google Drive
            result = self.google_drive.eliminar_archivo(solicitud.dictamen_final_file_id)
            
            if result['success']:
                # Limpiar campos de dictamen en la solicitud
                solicitud.dictamen_final_file_id = None
                solicitud.dictamen_final_url = None
                solicitud.fecha_resolucion = None
                
                db.session.commit()
                
                current_app.logger.info("Dictamen final eliminado exitosamente")
                return {
                    'success': True,
                    'message': 'Dictamen final eliminado exitosamente'
                }
            else:
                return result
                
        except Exception as e:
            current_app.logger.error(f"Error al eliminar dictamen final: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'error': f'Error inesperado al eliminar dictamen final: {str(e)}'
            }
    
    def manejar_cambio_estado(self, solicitud, estado_anterior, estado_nuevo):
        """
        Maneja los cambios de estado de una solicitud y las acciones relacionadas con el dictamen
        
        Args:
            solicitud (SolicitudEquivalencia): La solicitud de equivalencia
            estado_anterior (str): Estado anterior de la solicitud
            estado_nuevo (str): Nuevo estado de la solicitud
            
        Returns:
            dict: Resultado de las operaciones
        """
        try:
            current_app.logger.info(f"Manejando cambio de estado: {estado_anterior} -> {estado_nuevo}")
            
            # Si cambia a aprobada o rechazada, generar dictamen
            if estado_nuevo in ['aprobada', 'rechazada'] and estado_anterior not in ['aprobada', 'rechazada']:
                return self.generar_dictamen_final(solicitud)
            
            # Si vuelve a en_evaluacion desde un estado final, eliminar dictamen
            elif estado_nuevo == 'en_evaluacion' and estado_anterior in ['aprobada', 'rechazada']:
                return self.eliminar_dictamen_final(solicitud)
            
            # Si ya tenía dictamen y sigue en estado final, actualizar
            elif estado_nuevo in ['aprobada', 'rechazada'] and estado_anterior in ['aprobada', 'rechazada']:
                if solicitud.dictamen_final_file_id:
                    return self.actualizar_dictamen_final(solicitud)
                else:
                    return self.generar_dictamen_final(solicitud)
            
            # No se requiere acción para otros cambios de estado
            return {
                'success': True,
                'message': 'No se requiere acción para el dictamen final'
            }
            
        except Exception as e:
            current_app.logger.error(f"Error al manejar cambio de estado: {str(e)}")
            return {
                'success': False,
                'error': f'Error al manejar cambio de estado: {str(e)}'
            }
    
    def obtener_placeholders_disponibles(self):
        """
        Obtiene la lista de placeholders disponibles para usar en templates
        
        Returns:
            dict: Diccionario con categorías de placeholders
        """
        return self.placeholder_processor.get_available_placeholders()
