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
    
    # Asegurarse de que la carpeta de subida de archivos exista
    os.makedirs(os.path.join(app.root_path, 'static/uploads'), exist_ok=True)
    
    return app
