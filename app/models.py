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
    password_hash = db.Column(db.String(128), nullable=True)  # Make nullable for Keycloak users
    nombre = db.Column(db.String(64), nullable=False)
    apellido = db.Column(db.String(64), nullable=False)
    telefono = db.Column(db.String(20))
    rol = db.Column(db.String(20), nullable=False)  # 'admin', 'depto_estudiantes', 'evaluador'
    
    # Keycloak integration fields
    keycloak_id = db.Column(db.String(100), unique=True, nullable=True)  # Keycloak user ID
    is_keycloak_user = db.Column(db.Boolean, default=False)  # Flag to identify Keycloak users
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Campos específicos para evaluadores
    legajo_evaluador = db.Column(db.String(20), unique=True)
    departamento_academico = db.Column(db.String(100))
      # Relaciones
    solicitudes_asignadas = db.relationship('SolicitudEquivalencia', back_populates='evaluador')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        if self.is_keycloak_user:
            return False  # Keycloak users don't use local passwords
        return check_password_hash(self.password_hash, password)
    
    @classmethod
    def create_or_update_from_keycloak(cls, keycloak_user, keycloak_id, app_role):
        """Create or update user from Keycloak data"""
        print(f"DEBUG: create_or_update_from_keycloak called with role: {app_role}")
        user = cls.query.filter_by(keycloak_id=keycloak_id).first()
        
        if not user:
            # Check if user exists by email
            user = cls.query.filter_by(email=keycloak_user.get('email')).first()
            if user:
                # Update existing user with Keycloak data
                print(f"DEBUG: Found existing user by email: {user.username}, current role: {user.rol}")
                user.keycloak_id = keycloak_id
                user.is_keycloak_user = True
            else:
                # Create new user
                print(f"DEBUG: Creating new user with role: {app_role}")
                user = cls(
                    username=keycloak_user.get('preferred_username', keycloak_user.get('email')),
                    email=keycloak_user.get('email'),
                    nombre=keycloak_user.get('given_name', ''),
                    apellido=keycloak_user.get('family_name', ''),
                    rol=app_role,
                    keycloak_id=keycloak_id,
                    is_keycloak_user=True
                )
                db.session.add(user)
        else:
            print(f"DEBUG: Found existing user by keycloak_id: {user.username}, current role: {user.rol}")
        
        # Update user info (including role from Keycloak)
        print(f"DEBUG: Updating user role from {user.rol} to {app_role}")
        user.nombre = keycloak_user.get('given_name', user.nombre)
        user.apellido = keycloak_user.get('family_name', user.apellido)
        user.email = keycloak_user.get('email', user.email)
        user.rol = app_role  # Always update role to match Keycloak
        user.last_login = datetime.now()
        
        db.session.commit()
        print(f"DEBUG: User saved with final role: {user.rol}")
        return user
    
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

    # Firma digital del evaluador
    firma_evaluador = db.Column(db.String(255))

    # Documentación complementaria
    doc_complementaria_file_id = db.Column(db.String(100))  # ID del archivo complementario en Google Drive
    doc_complementaria_url = db.Column(db.String(500))  # URL del archivo complementario

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