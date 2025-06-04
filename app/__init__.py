import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Inicializar extensiones
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Configuración
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'clave-secreta-por-defecto')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///equivalencias.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configurar carpeta de uploads temporal
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp_uploads')
    # Asegurar que la carpeta existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Registrar blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.depto_estudiantes import depto_bp
    from app.routes.evaluadores import evaluadores_bp
    from app.routes.lector import lector_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(depto_bp)
    app.register_blueprint(evaluadores_bp)
    app.register_blueprint(lector_bp)
    # Endpoint para servir archivos privados de Google Drive
    from app.services.google_drive_service import GoogleDriveService
    from flask import send_file, abort
    import tempfile
    import io

    @app.route('/descargar_archivo_drive/<file_id>')
    def descargar_archivo_drive(file_id):
        # Solo usuarios autenticados pueden acceder
        from flask_login import current_user
        if not current_user.is_authenticated:
            abort(403)
        drive_service = GoogleDriveService()
        # Descargar el archivo usando Apps Script (debe implementar getFileContent en GAS y en el servicio Python)
        result = drive_service.obtener_contenido_archivo(file_id)
        if not result['success']:
            abort(404)
        # Decodificar base64
        import base64
        file_data = base64.b64decode(result['content'])
        return send_file(
            io.BytesIO(file_data),
            download_name=result.get('fileName', 'documento.pdf'),
            mimetype=result.get('mimeType', 'application/pdf')
        )
    
    # Asegurarse de que la carpeta de subida de archivos exista
    os.makedirs(os.path.join(app.root_path, 'static/uploads'), exist_ok=True)
    
    return app
