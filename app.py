import os
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from grafo_utils import db, grafo_a_imagen, camino_optimo_con_costera, obtener_ciudades
from sqlalchemy import text
from admin_routes import admin_bp

# Carga variables de entorno
load_dotenv()

# Inicializa la app Flask
app = Flask(__name__)
# Clave secreta para sesiones y cookies seguras
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'cambia_estasecret')
# Configuración de la base de datos
app.config.from_object(Config)

# Inicializa extensiones
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Registrar blueprint de administración
app.register_blueprint(admin_bp, url_prefix='/admin')

# Modelo de usuario
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin','user'), nullable=False, default='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Rutas de registro y autenticación
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash('Todos los campos son obligatorios', 'danger')
        elif Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'danger')
        else:
            new_user = Usuario(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Cuenta creada exitosamente, por favor inicia sesión', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = Usuario.query.filter_by(username=request.form['username']).first()
        if u and u.check_password(request.form['password']):
            login_user(u)
            flash(f"Bienvenido, {u.username}", "success")
            return redirect(url_for('index'))
        flash("Usuario o contraseña inválidos", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Ruta raíz redirige según rol
@app.route('/')
@login_required
def index():
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('camino_formulario'))

# Ruta fija (opcional) Ibarra → Loja
@app.route('/camino')
@login_required
def ver_camino():
    resultado = camino_optimo_con_costera('Ibarra', 'Loja')
    return render_template('camino.html', resultado=resultado)

# Rutas de usuario
@app.route('/grafo')
@login_required
def ver_grafo():
    return send_file(grafo_a_imagen(), mimetype='image/png')

@app.route('/camino_formulario', methods=['GET','POST'])
@login_required
def camino_formulario():
    ciudades = obtener_ciudades()
    resultado = None
    origen = destino = None
    if request.method == 'POST':
        origen = request.form.get('origen')
        destino = request.form.get('destino')
        if origen and destino and origen != destino:
            resultado = camino_optimo_con_costera(origen, destino)
    return render_template(
        'formulario.html', ciudades=ciudades,
        resultado=resultado, origen=origen, destino=destino
    )

@app.route('/check')
@login_required
def check_db():
    try:
        db.session.execute(text('SELECT 1'))
        return '✅ Conexión a la base de datos OK.'
    except Exception as e:
        return f'❌ Error de conexión: {e}'

@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.utcnow}


if __name__ == '__main__':
    app.run(debug=True)
