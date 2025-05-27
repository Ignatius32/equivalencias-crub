from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class Usuario(db.Model, UserMixin):
    """Modelo para los usuarios del sistema"""
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    nombre = db.Column(db.String(64), nullable=False)
    apellido = db.Column(db.String(64), nullable=False)
    telefono = db.Column(db.String(20))
    rol = db.Column(db.String(20), nullable=False)  # 'admin', 'depto_estudiantes', 'evaluador'
    
    # Campos específicos para evaluadores
    legajo_evaluador = db.Column(db.String(20), unique=True)
    departamento_academico = db.Column(db.String(100))
    
    # Relaciones
    solicitudes_asignadas = db.relationship('SolicitudEquivalencia', back_populates='evaluador')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Usuario {self.username} ({self.rol})>'


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


class SolicitudEquivalencia(db.Model):
    """Modelo para las solicitudes de equivalencia"""
    __tablename__ = 'solicitudes_equivalencia'
    
    id = db.Column(db.Integer, primary_key=True)
    id_solicitud = db.Column(db.String(10), unique=True, nullable=False)
    estado = db.Column(db.String(20), default='pendiente', nullable=False)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.now, nullable=False)
    fecha_resolucion = db.Column(db.DateTime, nullable=True)
    
    # Datos del solicitante
    nombre_solicitante = db.Column(db.String(64), nullable=False)
    apellido_solicitante = db.Column(db.String(64), nullable=False)
    dni_solicitante = db.Column(db.String(20), nullable=False)    
    legajo_crub = db.Column(db.String(20), nullable=False)
    correo_solicitante = db.Column(db.String(120), nullable=False)
    institucion_origen = db.Column(db.String(200), nullable=False)
    carrera_origen = db.Column(db.String(200), nullable=False)
    carrera_crub_destino = db.Column(db.String(200), nullable=False)
    observaciones_solicitante = db.Column(db.Text)
    
    # Relaciones
    evaluador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    evaluador = db.relationship('Usuario', back_populates='solicitudes_asignadas')
    dictamenes = db.relationship('Dictamen', back_populates='solicitud', cascade='all, delete-orphan')
      # Archivo adjunto
    id_archivo_solicitud = db.Column(db.String(100))
    ruta_archivo = db.Column(db.String(255))
    google_drive_file_id = db.Column(db.String(100))  # ID del archivo en Google Drive
    
    # Integración con Google Drive
    google_drive_folder_id = db.Column(db.String(100))
    google_drive_folder_name = db.Column(db.String(255))
    google_drive_folder_url = db.Column(db.String(500))
    
    # Dictamen final document
    dictamen_final_file_id = db.Column(db.String(100))  # ID del dictamen final en Google Drive
    dictamen_final_url = db.Column(db.String(500))  # URL del dictamen final
    
    def __repr__(self):
        return f'<SolicitudEquivalencia {self.id_solicitud} - {self.estado}>'


class Dictamen(db.Model):
    """Modelo para los dictámenes de equivalencia"""
    __tablename__ = 'dictamenes'

    id = db.Column(db.Integer, primary_key=True)
    asignatura_origen = db.Column(db.String(200), nullable=False)
    asignatura_destino = db.Column(db.String(200))
    tipo_equivalencia = db.Column(db.String(50))  # 'total', 'parcial', etc.
    observaciones = db.Column(db.Text)
    fecha_dictamen = db.Column(db.DateTime)
    
    # Relación con la solicitud
    solicitud_id = db.Column(db.Integer, db.ForeignKey('solicitudes_equivalencia.id'), nullable=False)
    solicitud = db.relationship('SolicitudEquivalencia', back_populates='dictamenes')
    
    # Relación con el evaluador
    evaluador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    evaluador = db.relationship('Usuario')
    
    def __repr__(self):
        return f'<Dictamen {self.id} - {self.asignatura_origen} -> {self.asignatura_destino}>'