from app import create_app, db
from app.models import Usuario, SolicitudEquivalencia, Dictamen
from datetime import datetime
import os
from werkzeug.security import generate_password_hash

app = create_app()

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Comando para inicializar la base de datos con datos de prueba
@app.cli.command("init-db")
def init_db():
    """Inicializar la base de datos con datos de prueba"""
    db.drop_all()
    db.create_all()
    
    print("Creando usuario administrador...")
    admin = Usuario(
        username="admin",
        email="admin@crub.uncoma.edu.ar",
        nombre="Administrador",
        apellido="Sistema",
        rol="admin"
    )
    admin.set_password("admin")
    db.session.add(admin)
    
    print("Creando usuario departamento estudiantes...")
    depto = Usuario(
        username="depto",
        email="depto.estudiantes@crub.uncoma.edu.ar",
        nombre="Departamento",
        apellido="Estudiantes",
        telefono="2944123456",
        rol="depto_estudiantes"
    )
    depto.set_password("depto")
    db.session.add(depto)
    
    print("Creando usuario evaluador...")
    evaluador = Usuario(
        username="evaluador",
        email="evaluador@crub.uncoma.edu.ar",
        nombre="María",
        apellido="López",
        telefono="2944654321",
        rol="evaluador",
        legajo_evaluador="123456",
        departamento_academico="Ingeniería"
    )
    evaluador.set_password("evaluador")
    db.session.add(evaluador)
    
    # Crear carpeta para archivos subidos
    os.makedirs(os.path.join(app.root_path, 'static/uploads'), exist_ok=True)
    
    # Guardar usuarios en la base de datos
    db.session.commit()
    
    print("Base de datos inicializada con éxito.")

if __name__ == '__main__':
    app.run(debug=True)  
