from datetime import datetime
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
      # Crear una solicitud de equivalencia de ejemplo
    print("Creando solicitud de equivalencia de ejemplo...")
    solicitud = SolicitudEquivalencia(
        id_solicitud="EQ-20250416-001",
        estado="pendiente",
        fecha_solicitud=datetime.now(),
        nombre_solicitante="Juan",
        apellido_solicitante="Pérez",
        dni_solicitante="30123456",
        legajo_crub="12345",
        correo_solicitante="juan.perez@example.com",
        institucion_origen="Universidad Nacional de Buenos Aires",
        carrera_origen="Licenciatura en Matemáticas",
        carrera_crub_destino="Licenciatura en Matemáticas",
        observaciones_solicitante="Solicito equivalencias para materias cursadas en UBA"
    )
    db.session.add(solicitud)
    db.session.flush()  # Para obtener el ID de la solicitud

    # Crear dictámenes de ejemplo
    print("Creando dictámenes de ejemplo...")
    dictamenes_data = [
        {
            "asignatura_origen": "Análisis Matemático I",
            "asignatura_destino": "Análisis Matemático I",
            "tipo_equivalencia": None,
            "observaciones": None
        },
        {
            "asignatura_origen": "Álgebra I y II",
            "asignatura_destino": "Álgebra",
            "tipo_equivalencia": None,
            "observaciones": None
        },
        {
            "asignatura_origen": "Física General",
            "asignatura_destino": "Física I",
            "tipo_equivalencia": None,
            "observaciones": None
        }
    ]

    for data in dictamenes_data:
        dictamen = Dictamen(
            asignatura_origen=data["asignatura_origen"],
            asignatura_destino=data["asignatura_destino"],
            tipo_equivalencia=data["tipo_equivalencia"],
            observaciones=data["observaciones"],
            solicitud_id=solicitud.id
        )
        db.session.add(dictamen)

    # Guardar todos los cambios en la base de datos
    db.session.commit()
    
    print("Base de datos inicializada con éxito.")
