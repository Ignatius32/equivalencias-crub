from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Usuario
from app import db
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
          # Validación especial para el admin (acceso rápido)
        if username == 'admin' and password == 'admin':
            user = Usuario.query.filter_by(username='admin').first()
            if not user:
                # Crear usuario admin si no existe
                user = Usuario(
                    username='admin',
                    email='admin@crub.uncoma.edu.ar',
                    nombre='Administrador',
                    apellido='Sistema',
                    rol='admin'
                )
                user.set_password('admin')
                db.session.add(user)
                db.session.commit()
            login_user(user, remember=remember)
            flash('¡Bienvenido Administrador!', 'success')
            return redirect(url_for('admin.index'))
        
        # Validación especial para depto_estudiantes (acceso rápido)
        elif username == 'depto' and password == 'depto':
            user = Usuario.query.filter_by(username='depto').first()
            if not user:
                # Crear usuario depto_estudiantes si no existe
                user = Usuario(
                    username='depto',
                    email='depto_estudiantes@crub.uncoma.edu.ar',
                    nombre='Departamento',
                    apellido='Estudiantes',
                    rol='depto_estudiantes'
                )
                user.set_password('depto')
                db.session.add(user)
                db.session.commit()
            login_user(user, remember=remember)
            flash('¡Bienvenido Departamento de Estudiantes!', 'success')
            return redirect(url_for('depto.list_equivalencias'))
        
        # Proceso normal de login para otros usuarios
        user = Usuario.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'¡Bienvenido {user.nombre}!', 'success')
            
            # Redirigir según el rol
            if user.rol == 'admin':
                return redirect(url_for('admin.index'))
            elif user.rol == 'depto_estudiantes':
                return redirect(url_for('depto.list_equivalencias'))
            elif user.rol == 'evaluador':
                return redirect(url_for('evaluadores.list_equivalencias'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('auth.login'))
