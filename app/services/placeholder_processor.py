# -*- coding: utf-8 -*-
from datetime import datetime
from flask import current_app


class PlaceholderProcessor:
    """Service for processing placeholders in document templates"""
    
    def __init__(self):
        """Initialize the placeholder processor"""
        pass
    def process_solicitud_placeholders(self, solicitud):
        """
        Process placeholders for a solicitud de equivalencia
        
        Args:
            solicitud (SolicitudEquivalencia): The solicitud object
            
        Returns:
            dict: Dictionary with placeholders and their values
        """
        try:
            # Basic solicitud information
            placeholders = {
                '{{ID_SOLICITUD}}': solicitud.id_solicitud or '',
                '{{FECHA_SOLICITUD}}': solicitud.fecha_solicitud.strftime('%d/%m/%Y') if solicitud.fecha_solicitud else '',
                '{{FECHA_RESOLUCION}}': solicitud.fecha_resolucion.strftime('%d/%m/%Y') if solicitud.fecha_resolucion else '',
                '{{ESTADO}}': self._format_estado(solicitud.estado) or '',
                
                # Solicitante information
                '{{NOMBRE_SOLICITANTE}}': solicitud.nombre_solicitante or '',
                '{{APELLIDO_SOLICITANTE}}': solicitud.apellido_solicitante or '',
                '{{NOMBRE_COMPLETO_SOLICITANTE}}': f"{solicitud.nombre_solicitante} {solicitud.apellido_solicitante}".strip(),
                '{{DNI_SOLICITANTE}}': solicitud.dni_solicitante or '',
                '{{LEGAJO_CRUB}}': solicitud.legajo_crub or '',
                '{{CORREO_SOLICITANTE}}': solicitud.correo_solicitante or '',
                
                # Academic information
                '{{INSTITUCION_ORIGEN}}': solicitud.institucion_origen or '',
                '{{CARRERA_ORIGEN}}': solicitud.carrera_origen or '',
                '{{CARRERA_CRUB_DESTINO}}': solicitud.carrera_crub_destino or '',
                '{{OBSERVACIONES_SOLICITANTE}}': solicitud.observaciones_solicitante or '',
                
                # Evaluator information
                '{{EVALUADOR_NOMBRE}}': solicitud.evaluador.nombre if solicitud.evaluador else '',
                '{{EVALUADOR_APELLIDO}}': solicitud.evaluador.apellido if solicitud.evaluador else '',
                '{{EVALUADOR_NOMBRE_COMPLETO}}': f"{solicitud.evaluador.nombre} {solicitud.evaluador.apellido}".strip() if solicitud.evaluador else '',
                '{{EVALUADOR_LEGAJO}}': solicitud.evaluador.legajo_evaluador if solicitud.evaluador else '',
                '{{EVALUADOR_DEPARTAMENTO}}': solicitud.evaluador.departamento_academico if solicitud.evaluador else '',
                
                # Current date
                '{{FECHA_ACTUAL}}': datetime.now().strftime('%d/%m/%Y'),
                '{{FECHA_ACTUAL_COMPLETA}}': datetime.now().strftime('%d de %B de %Y'),
                
                # Dictamenes list
                '{{DICTAMENES_TABLA}}': self._format_dictamenes_tabla(solicitud.dictamenes),
                '{{DICTAMENES_LISTA}}': self._format_dictamenes_lista(solicitud.dictamenes),
                
                # Counts
                '{{TOTAL_DICTAMENES}}': str(len(solicitud.dictamenes)),
                '{{TOTAL_EQUIVALENCIAS_APROBADAS}}': str(len([d for d in solicitud.dictamenes if d.tipo_equivalencia and 'total' in d.tipo_equivalencia.lower()])),
                '{{TOTAL_EQUIVALENCIAS_PARCIALES}}': str(len([d for d in solicitud.dictamenes if d.tipo_equivalencia and 'parcial' in d.tipo_equivalencia.lower()])),
            }
            
            return placeholders
            
        except Exception as e:
            current_app.logger.error(f"Error processing placeholders: {str(e)}")
            return {}
    
    def _format_estado(self, estado):
        """Format estado for display"""
        estado_map = {
            'pendiente': 'Pendiente',
            'en_evaluacion': 'En Evaluación',
            'aprobada': 'Aprobada',
            'rechazada': 'Rechazada'
        }
        return estado_map.get(estado, estado)
    
    def _format_dictamenes_tabla(self, dictamenes):
        """Format dictamenes as HTML table"""
        if not dictamenes:
            return "<p>No hay dictámenes registrados.</p>"
        
        html = """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th>Asignatura Origen</th>
                    <th>Asignatura Destino</th>
                    <th>Tipo de Equivalencia</th>
                    <th>Observaciones</th>
                    <th>Fecha</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for dictamen in dictamenes:
            fecha_str = dictamen.fecha_dictamen.strftime('%d/%m/%Y') if dictamen.fecha_dictamen else 'N/A'
            html += f"""
                <tr>
                    <td>{dictamen.asignatura_origen or ''}</td>
                    <td>{dictamen.asignatura_destino or 'N/A'}</td>
                    <td>{dictamen.tipo_equivalencia or 'N/A'}</td>
                    <td>{dictamen.observaciones or 'N/A'}</td>
                    <td>{fecha_str}</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        return html
    
    def _format_dictamenes_lista(self, dictamenes):
        """Format dictamenes as numbered list"""
        if not dictamenes:
            return "No hay dictámenes registrados."
        
        lista = []
        for i, dictamen in enumerate(dictamenes, 1):
            item = f"{i}. {dictamen.asignatura_origen}"
            if dictamen.asignatura_destino:
                item += f" → {dictamen.asignatura_destino}"
            if dictamen.tipo_equivalencia:
                item += f" ({dictamen.tipo_equivalencia})"
            if dictamen.observaciones:
                item += f" - {dictamen.observaciones}"
            lista.append(item)
        
        return '\n'.join(lista)
    
    def get_available_placeholders(self):
        """
        Get list of available placeholders for documentation
        
        Returns:
            dict: Dictionary with placeholder categories and their placeholders
        """
        return {
            'Información de Solicitud': [
                '{{ID_SOLICITUD}}',
                '{{FECHA_SOLICITUD}}',
                '{{FECHA_RESOLUCION}}',
                '{{ESTADO}}'
            ],
            'Información del Solicitante': [
                '{{NOMBRE_SOLICITANTE}}',
                '{{APELLIDO_SOLICITANTE}}',
                '{{NOMBRE_COMPLETO_SOLICITANTE}}',
                '{{DNI_SOLICITANTE}}',
                '{{LEGAJO_CRUB}}',
                '{{CORREO_SOLICITANTE}}'
            ],
            'Información Académica': [
                '{{INSTITUCION_ORIGEN}}',
                '{{CARRERA_ORIGEN}}',
                '{{CARRERA_CRUB_DESTINO}}',
                '{{OBSERVACIONES_SOLICITANTE}}'
            ],
            'Información del Evaluador': [
                '{{EVALUADOR_NOMBRE}}',
                '{{EVALUADOR_APELLIDO}}',
                '{{EVALUADOR_NOMBRE_COMPLETO}}',
                '{{EVALUADOR_LEGAJO}}',
                '{{EVALUADOR_DEPARTAMENTO}}'
            ],
            'Fechas': [
                '{{FECHA_ACTUAL}}',
                '{{FECHA_ACTUAL_COMPLETA}}'
            ],
            'Dictámenes': [
                '{{DICTAMENES_TABLA}}',
                '{{DICTAMENES_LISTA}}',
                '{{TOTAL_DICTAMENES}}',
                '{{TOTAL_EQUIVALENCIAS_APROBADAS}}',
                '{{TOTAL_EQUIVALENCIAS_PARCIALES}}'
            ]
        }
