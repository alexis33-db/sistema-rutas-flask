from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from grafo_utils import db, Provincia, Conexion, Ruta
from sqlalchemy.orm import aliased
from functools import wraps
import json
from collections import Counter

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorador interno para roles
def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash("No tienes permiso para acceder a esta página.", "warning")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

@admin_bp.route('/')
@login_required
@roles_required('admin')
def dashboard():
    # Conteo básico
    ciudades_count = Provincia.query.count()
    conexiones_count = db.session.query(Conexion).count()

    # Conteo de apariciones en rutas
    rutas = Ruta.query.all()
    contador = Counter()
    for ruta in rutas:
        try:
            camino = json.loads(ruta.camino)
            contador.update(camino)
        except Exception:
            continue

    # Top y bottom 5
    top_visitadas = contador.most_common(5)                    # [(ciudad, count), ...]
    menos_visitadas = sorted(contador.items(), key=lambda x: x[1])[:5]  # [(ciudad, count), ...]

    return render_template(
        'admin/dashboard.html',
        ciudades_count=ciudades_count,
        conexiones_count=conexiones_count,
        top_visitadas=top_visitadas,
        menos_visitadas=menos_visitadas
    )

# --- CRUD Ciudades ---

@admin_bp.route('/ciudades')
@login_required
@roles_required('admin')
def list_ciudades():
    ciudades = Provincia.query.order_by(Provincia.nombre).all()
    return render_template('admin/ciudades.html', ciudades=ciudades)

@admin_bp.route('/ciudades/nueva', methods=['GET','POST'])
@login_required
@roles_required('admin')
def nueva_ciudad():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        is_costera = 'is_costera' in request.form
        if not nombre:
            flash('El nombre no puede estar vacío', 'danger')
        else:
            try:
                db.session.add(Provincia(nombre=nombre, is_costera=is_costera))
                db.session.commit()
                flash('Ciudad agregada', 'success')
                return redirect(url_for('admin.list_ciudades'))
            except Exception:
                db.session.rollback()
                flash('Error: ciudad duplicada o inválida', 'danger')
    return render_template('admin/ciudad_form.html', accion='Crear', ciudad=None)

@admin_bp.route('/ciudades/editar/<int:id>', methods=['GET','POST'])
@login_required
@roles_required('admin')
def editar_ciudad(id):
    ciudad = Provincia.query.get_or_404(id)
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        is_costera = 'is_costera' in request.form
        if not nombre:
            flash('El nombre no puede estar vacío', 'danger')
        else:
            ciudad.nombre = nombre
            ciudad.is_costera = is_costera
            try:
                db.session.commit()
                flash('Ciudad actualizada', 'success')
                return redirect(url_for('admin.list_ciudades'))
            except Exception:
                db.session.rollback()
                flash('Error: nombre duplicado o inválido', 'danger')
    return render_template('admin/ciudad_form.html', accion='Editar', ciudad=ciudad)

@admin_bp.route('/ciudades/borrar/<int:id>', methods=['POST'])
@login_required
@roles_required('admin')
def borrar_ciudad(id):
    ciudad = Provincia.query.get_or_404(id)
    db.session.delete(ciudad)
    db.session.commit()
    flash('Ciudad eliminada', 'success')
    return redirect(url_for('admin.list_ciudades'))

# --- CRUD Conexiones ---

@admin_bp.route('/conexiones')
@login_required
@roles_required('admin')
def list_conexiones():
    Origen = aliased(Provincia)
    Destino = aliased(Provincia)
    conexiones = db.session.query(Conexion, Origen, Destino)\
        .join(Origen, Conexion.origen_id == Origen.id)\
        .join(Destino, Conexion.destino_id == Destino.id)\
        .all()
    return render_template('admin/conexiones.html', conexiones=conexiones)

@admin_bp.route('/conexiones/nueva', methods=['GET','POST'])
@login_required
@roles_required('admin')
def nueva_conexion():
    ciudades = Provincia.query.order_by(Provincia.nombre).all()
    if request.method == 'POST':
        origen_id = int(request.form['origen'])
        destino_id = int(request.form['destino'])
        distancia = request.form['distancia']
        if not distancia.isdigit() or int(distancia) <= 0:
            flash('Distancia inválida', 'danger')
        else:
            try:
                db.session.add(Conexion(
                    origen_id=origen_id,
                    destino_id=destino_id,
                    distancia=int(distancia)
                ))
                db.session.commit()
                flash('Conexión añadida', 'success')
                return redirect(url_for('admin.list_conexiones'))
            except Exception:
                db.session.rollback()
                flash('Error: conexión duplicada o datos inválidos', 'danger')
    return render_template(
        'admin/conexion_form.html',
        ciudades=ciudades,
        accion='Crear',
        conexion=None
    )

@admin_bp.route('/conexiones/editar/<int:id>', methods=['GET','POST'])
@login_required
@roles_required('admin')
def editar_conexion(id):
    conexion = Conexion.query.get_or_404(id)
    ciudades = Provincia.query.order_by(Provincia.nombre).all()
    if request.method == 'POST':
        origen_id = int(request.form['origen'])
        destino_id = int(request.form['destino'])
        distancia = request.form['distancia']
        if not distancia.isdigit() or int(distancia) <= 0:
            flash('Distancia inválida', 'danger')
        else:
            conexion.origen_id = origen_id
            conexion.destino_id = destino_id
            conexion.distancia = int(distancia)
            db.session.commit()
            flash('Conexión actualizada', 'success')
            return redirect(url_for('admin.list_conexiones'))
    return render_template(
        'admin/conexion_form.html',
        ciudades=ciudades,
        accion='Editar',
        conexion=conexion
    )

@admin_bp.route('/conexiones/borrar/<int:id>', methods=['POST'])
@login_required
@roles_required('admin')
def borrar_conexion(id):
    conexion = Conexion.query.get_or_404(id)
    db.session.delete(conexion)
    db.session.commit()
    flash('Conexión eliminada', 'success')
    return redirect(url_for('admin.list_conexiones'))
