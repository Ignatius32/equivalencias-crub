# Sistema de Gestión de Equivalencias CRUB

Sistema web desarrollado para gestionar solicitudes de equivalencia de asignaturas para el Centro Regional Universitario Bariloche (CRUB) de la Universidad Nacional del Comahue.

## Descripción

Este sistema permite gestionar el proceso completo de solicitudes de equivalencias académicas, desde la recepción de la solicitud hasta la resolución final. Está diseñado para tres tipos de usuarios:

1. **Departamento de Estudiantes**: Recibe y gestiona las solicitudes iniciales.
2. **Evaluadores**: Docentes que evalúan y emiten dictámenes sobre las equivalencias solicitadas.
3. **Administradores**: Gestión general del sistema, usuarios y supervisión de todos los procesos.

## Características principales

- Gestión de solicitudes de equivalencia académica
- Carga de documentación en formato digital (PDF)
- Sistema de dictámenes por asignatura (total, parcial o sin equivalencia)
- Seguimiento del estado de solicitudes (pendiente, en evaluación, aprobada, rechazada)
- Panel de administración para gestión de usuarios y visión general del sistema
- Interfaz responsive adaptada a diferentes dispositivos

## Tecnologías utilizadas

- **Backend**: Python 3.11+ con Flask 2.3.3
- **Base de datos**: SQLite (a través de SQLAlchemy)
- **Frontend**: HTML5, CSS3, JavaScript
- **Frameworks CSS**: Bootstrap 5
- **Dependencias principales**:
  - Flask-SQLAlchemy: ORM para interactuar con la base de datos
  - Flask-Login: Gestión de sesiones de usuario
  - Flask-Migrate: Migraciones de base de datos
  - Flask-WTF: Validación de formularios
  - python-dotenv: Gestión de variables de entorno

## Instalación

### Requisitos previos

- Python 3.11 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. Clonar el repositorio:
   ```
   git clone [URL_DEL_REPOSITORIO]
   cd equivalencias
   ```

2. Crear y activar un entorno virtual (recomendado):
   ```
   python -m venv venv
   
   # En Windows
   venv\Scripts\activate
   
   # En macOS/Linux
   source venv/bin/activate
   ```

3. Instalar las dependencias:
   ```
   pip install -r requirements.txt
   ```

4. Crear un archivo `.env` en la raíz del proyecto (o usar el existente) con la siguiente configuración:
   ```
   FLASK_APP=app
   FLASK_ENV=development
   SECRET_KEY=tu_clave_secreta_muy_segura
   DATABASE_URL=sqlite:///equivalencias.db
   ```

5. Inicializar la base de datos:
   ```
   python init_db.py
   ```

6. Ejecutar la aplicación:
   ```
   flask run
   ```

7. Abrir en el navegador: `http://localhost:5000`

## Estructura del proyecto

```
equivalencias/
├── app/                      # Directorio principal de la aplicación
│   ├── __init__.py           # Inicialización de la aplicación Flask
│   ├── models.py             # Modelos de base de datos
│   ├── routes/               # Rutas y controladores
│   │   ├── admin.py          # Rutas para administradores
│   │   ├── auth.py           # Rutas de autenticación
│   │   ├── depto_estudiantes.py  # Rutas para depto. estudiantes
│   │   └── evaluadores.py    # Rutas para evaluadores
│   ├── static/               # Archivos estáticos (CSS, JS, imágenes)
│   │   ├── css/              # Hojas de estilo
│   │   └── uploads/          # Archivos subidos por los usuarios
│   └── templates/            # Plantillas HTML
│       ├── admin/            # Plantillas para administradores
│       ├── auth/             # Plantillas de autenticación
│       ├── depto_estudiantes/ # Plantillas para depto. estudiantes
│       ├── evaluadores/      # Plantillas para evaluadores
│       └── base.html         # Plantilla base
├── instance/                 # Directorio para la base de datos SQLite
├── app.py                    # Punto de entrada de la aplicación
├── init_db.py                # Script para inicializar la base de datos
├── requirements.txt          # Dependencias del proyecto
└── .env                      # Variables de entorno
```

## Usuario por defecto

Para acceder al sistema por primera vez, utilice:

- **Usuario**: admin
- **Contraseña**: admin

También está disponible:
- **Usuario**: depto
- **Contraseña**: depto

- **Usuario**: evaluador
- **Contraseña**: evaluador

## Flujo de trabajo

1. **Departamento de Estudiantes** 
   - Crea nuevas solicitudes
   - Asigna evaluadores
   - Gestiona documentación

2. **Evaluadores**
   - Revisan solicitudes asignadas
   - Emiten dictámenes por asignatura
   - Resuelven solicitudes (aprobación/rechazo)

3. **Administradores**
   - Gestionan usuarios
   - Tienen acceso completo al sistema
   - Visualizan estadísticas en el dashboard

## Contribuir

Para contribuir al proyecto:

1. Hacer fork del repositorio
2. Crear una rama para tu función: `git checkout -b nueva-funcion`
3. Hacer commit de tus cambios: `git commit -m 'Agregar nueva función'`
4. Hacer push a la rama: `git push origin nueva-funcion`
5. Enviar un Pull Request

## Autor

Centro Regional Universitario Bariloche - Universidad Nacional del Comahue

## Licencia

Este proyecto es software propietario del Centro Regional Universitario Bariloche.
