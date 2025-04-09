from app import create_app, db
from app.models import Usuario, SolicitudEquivalencia, Dictamen

app = create_app()
with app.app_context():
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
    import os
    os.makedirs(os.path.join(app.root_path, 'static/uploads'), exist_ok=True)
    
    # Guardar usuarios en la base de datos
    db.session.commit()
    
    print("Base de datos inicializada con éxito.")
