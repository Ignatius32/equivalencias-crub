# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from app.models import SolicitudEquivalencia

lector_bp = Blueprint("lector", __name__, url_prefix="/lector")

def lector_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != "lector":
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

@lector_bp.route("/equivalencias")
@login_required
@lector_required
def list_equivalencias():
    solicitudes = SolicitudEquivalencia.query.all()
    return render_template("lector/list_equivalencias.html", solicitudes=solicitudes)

@lector_bp.route("/equivalencias/ver/<int:id>")
@login_required
@lector_required
def view_equivalencia(id):
    solicitud = SolicitudEquivalencia.query.get_or_404(id)
    return render_template("lector/view_equivalencia.html", solicitud=solicitud)
