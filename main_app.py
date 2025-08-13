from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
import os # Aunque no lo uses para MAIL_USERNAME/PASS, puede ser necesario para UPLOAD_FOLDER o similar
from werkzeug.utils import secure_filename
# En la seccion de importaciones al principio de tu main_alol.py
from flask_security.utils import hash_password # <--- Esta es la linea clave
# --- Importaciones de Flask-Security-Too ---
from flask_security import Security, SQLAlchemySessionUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user, roles_required, \
    anonymous_user_required, logout_user
import json
import urllib.parse
import random
import requests
# --- Importaciones de Flask-Mail ---
from flask_mail import Mail

# --- Importaciones adicionales necesarias ---
import uuid
from datetime import datetime


# --- ConfiguraciÃ³n de la AplicaciÃ³n Flask ---
db_user = 'Setatt'
db_password = 'carlasebas1*'
db_host = 'Setatt.mysql.pythonanywhere-services.com'
db_name = 'Setatt$default'


app = Flask(__name__)
DATABASE_URI = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'f1c5d9a8e0b2c3d4e5f6a762hey7b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8'


# --- Configuracion para la subida de archivos (productos) ---
UPLOAD_FOLDER_PRODUCTS = os.path.join(app.root_path, 'static', 'product_images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER_PRODUCTS'] = UPLOAD_FOLDER_PRODUCTS
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

if not os.path.exists(UPLOAD_FOLDER_PRODUCTS):
    os.makedirs(UPLOAD_FOLDER_PRODUCTS)

# --- Configuracion para la subida de archivos (categorias) ---
UPLOAD_FOLDER_CATEGORIES = os.path.join(app.root_path, 'static', 'category_images')
app.config['UPLOAD_FOLDER_CATEGORIES'] = UPLOAD_FOLDER_CATEGORIES

if not os.path.exists(UPLOAD_FOLDER_CATEGORIES):
    os.makedirs(UPLOAD_FOLDER_CATEGORIES)

# --- ConfiguraciÃ³n Especifica de Flask-Security-Too ---
app.config['SECURITY_PASSWORD_SALT'] = 'otra-clave-aleatoria-y-unica-para-flask-security' # CAMBIAR ESTO EN PRODUCCIÃ“N
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False
app.config['SECURITY_CONFIRMABLE'] = False
app.config['SECURITY_RECOVERABLE'] = True
app.config['SECURITY_CHANGEABLE'] = True
app.config['SECURITY_LOGIN_WITHOUT_CONFIRMATION'] = False

app.config['SECURITY_LOGIN_USER_TEMPLATE'] = 'login.html'

app.config['SECURITY_POST_REGISTER_VIEW'] = '/register-success'

app.config['SECURITY_REGISTER_USER_TEMPLATE'] = 'register.html'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'anaveleci@gmail.com '
app.config['MAIL_PASSWORD'] = 'kzco ozhl akli ojf'
app.config['MAIL_DEFAULT_SENDER'] = 'anaveleci@gmail.com'


# --- InicializaciÃ³n de SQLAlchemy y Flask-Mail ---
db = SQLAlchemy(app)
mail = Mail(app)

# --- Definicion de Modelos de Base de Datos ---

# Modelo para Roles, requerido por Flask-Security
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(15), unique=True, nullable=True)
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
    active = db.Column(db.Boolean(), default=True)
    confirmed_at = db.Column(db.DateTime())
    nombre_completo = db.Column(db.String(100), nullable=True)
    telefono = db.Column(db.String(25), nullable=True)
    # ---------------------

    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __repr__(self):
        return f"User('{self.email}')"


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Role {self.name}>'

# --- Modelos de bingo ---

class Serial(db.Model):
    __tablename__ = 'serial'
    id = db.Column(db.Integer, primary_key=True)
    serial_number = db.Column(db.String(80), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('serials', lazy='dynamic'))
    bingo_cards = db.relationship('BingoCard', backref='serial', lazy=True)


class BingoCard(db.Model):
    __tablename__ = 'bingo_card'
    id = db.Column(db.Integer, primary_key=True)
    serial_id = db.Column(db.Integer, db.ForeignKey('serial.id'), nullable=False)
    card_data = db.Column(db.String(500), nullable=True)


class GameSession(db.Model):
    __tablename__ = 'game_session'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50), nullable=False, default='waiting') # 'waiting', 'active', 'paused', 'finished'
    numbers_called = db.Column(db.Text, nullable=True)
    current_calling_number = db.Column(db.Integer, nullable=True)
    call_start_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Campos para el bingo pendiente de verificación
    pending_bingo_serial = db.Column(db.String(80), nullable=True)
    pending_bingo_card_data = db.Column(db.Text, nullable=True)

    # ¡NUEVOS CAMPOS PARA EL GANADOR!
    winner_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    winning_card_data = db.Column(db.Text, nullable=True)
    winning_serial = db.Column(db.String(80), nullable=True)

    # Relación para acceder fácilmente al objeto User del ganador
    winner = db.relationship('User', foreign_keys=[winner_user_id])


    def get_numbers_called(self):
        if self.numbers_called:
            try:
                return json.loads(self.numbers_called)
            except json.JSONDecodeError:
                return []
        return []




class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship('User', backref=db.backref('chat_messages', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'message_text': self.message_text,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

    def __repr__(self):
        return f'<ChatMessage {self.id} by {self.username}>'


class AvailableCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_number = db.Column(db.Integer, unique=True, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    occupied_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<AvailableCard {self.card_number} (Available: {self.is_available})>'

user_datastore = SQLAlchemySessionUserDatastore(db.session, User, Role)
security = Security(app, user_datastore)

# --- Funciones de utilidad ---
def allowed_file(filename):
    """Verifica si la extensiÃ³n del archivo estÃ¡ permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Variables de Telegram (si las sigues usando para notificaciones) ---
BOT_TOKEN = "7856660382:AAEr3ISJ70rw24vP-9Nyf7ekHoEWjAgtoUw" # Ejemplo
CHAT_ID = "-1002662659767" # Ejemplo


# --- Funciones de Bingo ---

def generate_bingo_card():
    """
    Genera un cartón de bingo con 5 números por columna (B, I, N, G, O),
    con el centro 'FREE' y sin repeticiones dentro de cada columna.
    """
    card = {
        'B': sorted(random.sample(range(1, 16), 5)),
        'I': sorted(random.sample(range(16, 31), 5)),
        'N': sorted(random.sample(range(31, 46), 5)),
        'G': sorted(random.sample(range(46, 61), 5)),
        'O': sorted(random.sample(range(61, 76), 5))
    }
    # El espacio central (N3) se establece como 'FREE'
    card['N'][2] = 'FREE'
    return card

def format_bingo_card_as_text_for_telegram(card_data, transaction_serial_uuid):

    header = "B    I    N    G    O\n"
    separator = "-----------------------\n"
    card_rows = []

    N_COL_WIDTH = 7

    for i in range(5):
        b = str(card_data['B'][i]).ljust(3)
        i_col = str(card_data['I'][i]).ljust(3)
        n_val = str(card_data['N'][i])
        n = n_val.ljust(N_COL_WIDTH)
        g = str(card_data['G'][i]).ljust(3)
        o = str(card_data['O'][i]).ljust(3)

        card_rows.append(f"{b} {i_col} {n} {g} {o}")

    card_text = header + separator + "\n".join(card_rows) + "\n" + separator
    card_text += f"Serial de Transacción: {transaction_serial_uuid}"

    return card_text

# --- FIN DE LAS FUNCIONES DE BINGO ---

@app.route('/')
def index():
    """Renderiza la página principal (menú) donde están los enlaces."""
    active_games = GameSession.query.filter(GameSession.status.in_(['pending', 'active'])).all()
    return render_template('index_2.html', active_games=active_games)

@app.before_request
def check_profile_completion():
    g.show_profile_modal = False
    if current_user.is_authenticated and not current_user.is_anonymous:
        profile_incomplete = not current_user.username or not current_user.telefono
        is_safe_endpoint = request.endpoint in ['static', 'complete_profile', 'security.logout']

        if profile_incomplete and not is_safe_endpoint:
            g.show_profile_modal = True

@app.route('/pagina_en_desarrollo', methods=['GET', 'POST'])
@login_required
def pagina_en_desarrollo():
    if request.method == 'POST':
        telefono = request.form['telefono']
        numeros_carton_str = request.form['numeros_carton']
        imagen_pago = request.files['imagen_pago']

        try:
            numeros_carton = [int(n) for n in numeros_carton_str.split(',')]
            for numero_carton in numeros_carton:
                if not (1 <= numero_carton <= 100):
                    return jsonify({'error': f'numero de carton {numero_carton} fuera de rango (1-100)'}), 400

                existing_occupied_card = AvailableCard.query.filter_by(card_number=numero_carton, is_available=False).first()
                if existing_occupied_card:
                    return jsonify({'error': f'El numero de carton {numero_carton} ya esta ocupado. Por favor, elija otro.'}), 409

        except ValueError:
            return jsonify({'error': 'Lista de numeros de carton invalido. Deben ser numeros enteros separados por comas.'}), 400

        temp_user_payment_image_path = 'temp_user_payment.jpg'
        imagen_pago.save(temp_user_payment_image_path)

        serial_number_generated = str(uuid.uuid4())
        new_serial = Serial(
            serial_number=serial_number_generated,
            user_id=current_user.id  # <-- ¡Aquí está la magia!
        )

        db.session.add(new_serial)
        db.session.flush()

        try:
            bingo_cards_data = []
            bingo_cards_formatted_for_telegram = []

            for numero_carton in numeros_carton:
                bingo_card_data = generate_bingo_card()

                bingo_card_data['N'][2] = f"C-{numero_carton}"

                bingo_card_json = json.dumps(bingo_card_data)
                new_bingo_card_entry = BingoCard(
                    card_data=bingo_card_json,
                    serial_id=new_serial.id
                )
                db.session.add(new_bingo_card_entry)
                print(f"Carton de bingo para el numero {numero_carton} preparado para guardar.")

                occupied_card_entry = AvailableCard.query.filter_by(card_number=numero_carton).first()
                if occupied_card_entry:
                    occupied_card_entry.is_available = False
                    occupied_card_entry.occupied_at = db.func.current_timestamp()
                else:
                    occupied_card_entry = AvailableCard(card_number=numero_carton, is_available=False, occupied_at=db.func.current_timestamp())
                    db.session.add(occupied_card_entry)

                bingo_cards_data.append(bingo_card_data)

                formatted_card_text = format_bingo_card_as_text_for_telegram(
                    bingo_card_data,
                    serial_number_generated
                )
                bingo_cards_formatted_for_telegram.append(formatted_card_text)

            db.session.commit()
            print(f"Cartones de bingo guardados para el serial {serial_number_generated}")

        except Exception as e:
            db.session.rollback()
            print(f"Error al guardar los cartones de bingo: {e}")
            if os.path.exists(temp_user_payment_image_path):
                os.remove(temp_user_payment_image_path)
            return jsonify({'error': 'Error interno al procesar los cartones.'}), 500

        # --- Envío de la foto con su caption (sin parse_mode) ---
        url_photo = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files_payment = {'photo': open(temp_user_payment_image_path, 'rb')}
        caption_payment = f'Telefono: {telefono}\nCartones del Usuario: {numeros_carton_str}\nSerial de Transaccion: {serial_number_generated}'
        r_payment = requests.post(url_photo, files=files_payment, data={'chat_id': CHAT_ID, 'caption': caption_payment})
        print(f"DEBUG: sendPhoto status: {r_payment.status_code}, response: {r_payment.text}")

        # --- Construyendo y enviando el mensaje con los cartones (en texto plano) ---
        full_cards_message = "¡Aquí tienes tus cartones de Bingo!\n\n" + "\n\n".join(bingo_cards_formatted_for_telegram)
        full_cards_message += f"\n\nTeléfono de contacto asociado: {telefono}"

        print(f"DEBUG: Longitud del mensaje de cartones: {len(full_cards_message)} caracteres.")

        url_message = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        r_bingo_card_text = requests.post(url_message, json={'chat_id': CHAT_ID, 'text': full_cards_message})
        print(f"DEBUG: sendMessage status: {r_bingo_card_text.status_code}, response: {r_bingo_card_text.text}")

        if os.path.exists(temp_user_payment_image_path):
            os.remove(temp_user_payment_image_path)

        if r_payment.status_code == 200 and r_bingo_card_text.status_code == 200:
            return render_template('bingo_display.html', cards=bingo_cards_data, serial=serial_number_generated)

        else:
            db.session.rollback()
            print("Error al enviar a Telegram. Rollback de la transacción de DB.")
            return f"Error al enviar la imagen de pago o el cartón de bingo a Telegram. Pago: {r_payment.text}, Cartón: {r_bingo_card_text.text if 'r_bingo_card_text' in locals() else 'No se intentó enviar el cartón'}"

    return render_template('desarrollo.html')

@app.route('/complete-profile', methods=['POST'])
@login_required
def complete_profile():
    """
    Ruta para recibir los datos del modal y actualizar el perfil del usuario.
    """
    try:
        nombre = request.form.get('nombre_completo')
        tel = request.form.get('telefono')

        if not nombre or not tel:
            return jsonify({'success': False, 'message': 'Todos los campos son requeridos.'}), 400

        # Actualizamos los datos del usuario actual
        user = current_user
        user.username = nombre
        user.telefono = tel

        db.session.commit()

        flash('¡Gracias por completar tu perfil!', 'success')
        return jsonify({'success': True, 'message': 'Perfil actualizado correctamente.'})

    except Exception as e:
        db.session.rollback()
        print(f"Error al actualizar perfil: {e}")
        return jsonify({'success': False, 'message': 'Ocurrió un error interno.'}), 500

@app.route('/mis_cartones')
@login_required
def mis_cartones():
    """
    Muestra todos los cartones de bingo asociados a la cuenta del usuario logueado.
    """
    # Buscamos todos los seriales que pertenecen al usuario actual.
    user_serials = Serial.query.filter_by(user_id=current_user.id).order_by(Serial.id.desc()).all()

    if not user_serials:
        # El usuario no tiene cartones, le mostramos un mensaje amigable.
        flash("Aún no tienes cartones de bingo. ¡Compra uno para empezar a jugar!", "info")
        return render_template('mis_cartones.html', all_cards_data=[])

    all_cards_data = []
    # Recorremos cada serial del usuario para recolectar sus cartones.
    for serial in user_serials:
        for card in serial.bingo_cards:
            try:
                card_data_json = json.loads(card.card_data) if card.card_data else {}
                # Tu lógica de reestructuración de datos de cartón
                # (la he copiado de tu ruta ver_carton_con_bingo)
                reestructurado_numeros = {}
                if isinstance(card_data_json, dict):
                    reestructurado_numeros = card_data_json
                else:
                    print(f"Formato de datos de cartón inesperado para BingoCard ID {card.id}")
                    continue

                all_cards_data.append({
                    'card_id': f"card{card.id}",
                    'card_data': reestructurado_numeros,
                    'serial_number': serial.serial_number  # Lo pasamos por si lo necesitas en el template
                })
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error procesando BingoCard ID {card.id}: {e}")
                continue

    # Ahora reutilizamos el template 'ver_carton_integrado.html' pero le pasamos todos los cartones.
    # O puedes crear un nuevo template 'mis_cartones.html' si el layout es muy diferente.
    # Por simplicidad, usemos el que ya tienes.

    # Lógica para obtener el juego activo (igual que en tu ruta original)
    active_game = GameSession.query.filter_by(status='active').order_by(GameSession.created_at.desc()).first()
    game_info = None
    numbers_called_as_strings = []
    current_calling_number = None
    call_start_time_timestamp = None

    if active_game:
        # ... (copia y pega aquí toda la lógica de 'active_game' que tienes en 'ver_carton_con_bingo')
        current_numbers_called = active_game.get_numbers_called()
        if current_numbers_called:
            numbers_called_as_strings = [str(num) for num in current_numbers_called]
        game_info = {'game_id': active_game.id, 'status': active_game.status}
        current_calling_number = active_game.current_calling_number
        if active_game.call_start_time:
            call_start_time_timestamp = int(active_game.call_start_time.timestamp() * 1000)


    return render_template('mis_cartones.html', # O un nuevo 'mis_cartones.html'
                           cards=all_cards_data,
                           # Ya no pasamos un serial_number específico, la vista es general
                           serial_number=None, # O podrías pasar el del primer cartón si lo necesitas
                           game_info=game_info,
                           numbers_called_as_strings=numbers_called_as_strings,
                           current_calling_number=current_calling_number,
                           call_start_time_timestamp=call_start_time_timestamp
                          )

@app.route('/api/call_bingo', methods=['POST'])
def call_bingo():
    """
    Endpoint para que un jugador cante bingo.
    Pausa el juego y guarda los datos del cartÃ³n para verificaciÃ³n.
    """
    data = request.get_json()
    serial_number = data.get('serial_number')
    card_data = data.get('card_data')

    if not serial_number or not card_data:
        return jsonify({'error': 'Faltan datos del serial o del cartÃ³n.'}), 400

    active_game = GameSession.query.filter_by(status='active').first()

    if not active_game:
        return jsonify({'error': 'No hay una partida activa para cantar bingo.'}), 400

    # Si alguien mÃ¡s ya cantÃ³, el estado serÃ¡ 'paused'
    if active_game.pending_bingo_serial:
        return jsonify({'error': 'Alguien mÃ¡s ya ha cantado bingo. Por favor, espera a la verificaciÃ³n.'}), 409

    # Pausar el juego y guardar los datos
    active_game.status = 'paused'
    active_game.pending_bingo_serial = serial_number
    active_game.pending_bingo_card_data = json.dumps(card_data) # Guardamos el cartÃ³n como JSON

    # Detener cualquier temporizador de nÃºmero en curso
    active_game.current_calling_number = None
    active_game.call_start_time = None

    db.session.commit()

    # (Opcional) Enviar notificaciÃ³n a Telegram al admin
    card_number = card_data.get('N', [])[2] # Extraer el C-XX
    message_to_admin = f"Â¡BINGO CANTADO!\n\nSerial: {serial_number}\nNÃºmero de CartÃ³n: {card_number}\n\nEl juego estÃ¡ en pausa. Por favor, verifica en el panel de administraciÃ³n."
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={'chat_id': CHAT_ID, 'text': message_to_admin})

    return jsonify({'message': 'Â¡Bingo recibido! Un administrador verificarÃ¡ tu cartÃ³n. El juego ha sido pausado.'}), 200

@app.route('/admin/bingo/confirm', methods=['POST'])
@login_required
@roles_required("admin")
def confirm_bingo():
    """
    Confirma el bingo, guarda los datos del ganador y termina la partida.
    """
    paused_game = GameSession.query.filter_by(status='paused').first()
    if not paused_game:
        flash("No se encontró una partida en pausa para confirmar.", "error")
        return redirect(url_for('admin_bingo_panel'))

    # Obtener el serial y los datos del cartón que cantó bingo
    serial_number = paused_game.pending_bingo_serial
    card_data_json = paused_game.pending_bingo_card_data

    if not serial_number or not card_data_json:
        flash("No hay datos de bingo pendientes para confirmar.", "warning")
        return redirect(url_for('admin_bingo_panel'))

    # Buscar al usuario ganador a través del serial
    winning_serial_obj = Serial.query.filter_by(serial_number=serial_number).first()
    if not winning_serial_obj or not winning_serial_obj.user_id:
        flash(f"No se pudo encontrar un usuario asociado al serial {serial_number}.", "error")
        return redirect(url_for('admin_bingo_panel'))

    # Guardar la información del ganador en la sesión del juego
    paused_game.status = 'finished'
    paused_game.winner_user_id = winning_serial_obj.user_id
    paused_game.winning_serial = serial_number
    paused_game.winning_card_data = card_data_json

    # Limpiar los campos pendientes
    paused_game.pending_bingo_serial = None
    paused_game.pending_bingo_card_data = None

    db.session.commit()

    flash(f"¡Bingo confirmado para el usuario {winning_serial_obj.user.username}!", "success")
    return redirect(url_for('admin_bingo_panel'))


@app.route('/admin/bingo/reject', methods=['POST'])
def reject_bingo():
    """Rechaza el bingo y reanuda la partida."""
    paused_game = GameSession.query.filter_by(status='paused').first()
    if paused_game:
        paused_game.status = 'active' # Vuelve a estado activo
        paused_game.pending_bingo_serial = None # Limpia los datos del bingo falso
        paused_game.pending_bingo_card_data = None
        db.session.commit()
    return redirect(url_for('admin_bingo_panel'))


@app.route('/felicidades/<int:game_id>')
@login_required
def felicidades(game_id):
    """
    Página de felicitación para el ganador del bingo.
    """
    # Busca la partida finalizada
    game = GameSession.query.filter_by(id=game_id, status='finished').first_or_404()

    # Medida de seguridad: solo el ganador puede ver esta página
    if game.winner_user_id != current_user.id:
        flash("No tienes permiso para ver esta página.", "danger")
        return redirect(url_for('index'))

    # Extraer los datos para el mensaje de WhatsApp
    serial = game.winning_serial
    try:
        card_data = json.loads(game.winning_card_data)
        # El número del cartón está en la posición 2 de la columna 'N'
        card_number = card_data.get('N', ['','',''])[2]
    except (json.JSONDecodeError, IndexError):
        card_number = "Desconocido"

    # --- CONFIGURA TU NÚMERO Y MENSAJE AQUÍ ---
    # IMPORTANTE: Reemplaza '58xxxxxxxxxx' con tu número de WhatsApp real en formato internacional (sin '+', ni '00')
    tu_numero_whatsapp = "584142542522"

    mensaje_base = (
        f"¡Hola! He ganado el bingo a cartón lleno en la partida: {game.id} "
        f"con el cartón número: {card_number} "
        f"y el serial: {serial}"
    )

    # Codificamos el mensaje para que sea seguro en una URL
    mensaje_codificado = urllib.parse.quote(mensaje_base)

    # Construimos el enlace final de WhatsApp
    whatsapp_link = f"https://api.whatsapp.com/send?phone={tu_numero_whatsapp}&text={mensaje_codificado}"

    return render_template('felicidades.html',
                           game=game,
                           serial=serial,
                           card_number=card_number,
                           whatsapp_link=whatsapp_link)



@app.route('/chat/send_message', methods=['POST'])
@login_required
def send_chat_message():
    """Endpoint para que un usuario envíe un mensaje al chat."""
    data = request.get_json()
    message_text = data.get('message')

    if not message_text:
        return jsonify({'error': 'El mensaje no puede estar vacío.'}), 400

    # Crear y guardar el nuevo mensaje
    new_message = ChatMessage(
        user_id=current_user.id,
        username=current_user.username, # Asumiendo que tienes un campo username
        message_text=message_text
    )
    db.session.add(new_message)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Mensaje enviado.'}), 201


@app.route('/chat/get_messages')
@login_required
def get_chat_messages():
    """
    Endpoint para que el cliente pida los mensajes nuevos.
    Usa el parámetro 'since_id' para obtener solo los mensajes
    que han llegado después del último que tiene el cliente.
    """
    last_id = request.args.get('since_id', 0, type=int)

    # Busca mensajes más nuevos que el último ID conocido
    # Limita la cantidad para no sobrecargar, ej: los últimos 100 mensajes nuevos
    messages = ChatMessage.query.filter(ChatMessage.id > last_id)\
                                .order_by(ChatMessage.timestamp.asc())\
                                .limit(100)\
                                .all()

    # Convierte los mensajes a un formato JSON
    messages_data = [msg.to_dict() for msg in messages]

    return jsonify(messages_data)


# --- RUTAS DE ADMINISTRACIÓN ---


@app.route('/tu_pagina_secreta')
@login_required
@roles_required("admin")
def pagina_secreta():
    # Esta ruta debería ser protegida por autenticación
    return render_template('cartones.html')

@app.route('/api/reset_disponibilidad', methods=['POST'])
@login_required
@roles_required("admin")
def reset_disponibilidad():
    try:
        # 1. Eliminar todos los registros de BingoCard (depende de Serial)
        num_deleted_bingo_cards = db.session.query(BingoCard).delete()

        # 2. Eliminar todos los registros de Serial
        num_deleted_serials = db.session.query(Serial).delete()

        # 3. Eliminar todos los registros de AvailableCard
        num_deleted_available_cards = db.session.query(AvailableCard).delete()

        # 5. Elimina todos los registros de ChatMessage
        num_deleted_ChatMessage = db.session.query(ChatMessage).delete()

        db.session.commit()

        return jsonify({
            'message': 'Base de datos completamente reseteada.',
            'details': {
                'cartones_bingo_eliminados': num_deleted_bingo_cards,
                'seriales_transaccion_eliminados': num_deleted_serials,
                'disponibilidad_cartones_eliminada': num_deleted_available_cards,
                'chat eliminado': num_deleted_ChatMessage
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error al resetear todos los datos: {e}")
        return jsonify({'error': 'Error interno al resetear todos los datos.'}), 500


@app.route('/api/delete_disponibilidad/<int:card_number>', methods=['DELETE'])
@login_required
@roles_required("admin")
def delete_disponibilidad(card_number):
    try:
        # Busca el registro del número de cartón específico
        card_to_delete = AvailableCard.query.filter_by(card_number=card_number).first()

        if card_to_delete:
            db.session.delete(card_to_delete) # Elimina el registro
            db.session.commit() # Guarda los cambios en la base de datos
            return jsonify({'message': f'Cartón {card_number} ha sido eliminado de la lista de ocupados (ahora disponible).'}), 200
        else:
            return jsonify({'error': f'El cartón {card_number} no se encontró como ocupado.'}), 404

    except Exception as e:
        db.session.rollback() # Si algo sale mal, deshaz los cambios
        print(f"Error al eliminar el cartón {card_number}: {e}")
        return jsonify({'error': 'Error interno al intentar eliminar el cartón.'}), 500

# --- ENDPOINT ADICIONAL (TU RUTA ORIGINAL) ---
@app.route('/api/numeros_ocupados')
def get_numeros_ocupados():
    """Endpoint para obtener la lista de números de cartón que ya están ocupados."""
    try:
        occupied_cards = AvailableCard.query.filter_by(is_available=False).all()
        numeros_ocupados = [card.card_number for card in occupied_cards]
        return jsonify({'ocupados': numeros_ocupados})
    except Exception as e:
        print(f"Error al obtener números ocupados de la DB: {e}")
        return jsonify({'error': 'Error al cargar la disponibilidad.'}), 500

# --- NUEVAS RUTAS Y FUNCIONES PARA EL PANEL DE ADMINISTRACIÓN DE BINGO ---

@app.route('/admin/bingo')
@login_required
@roles_required("admin")
def admin_bingo_panel():
    # Busca una partida activa O pausada
    game = GameSession.query.filter(GameSession.status.in_(['active', 'paused'])).order_by(GameSession.created_at.desc()).first()

    if not game:
        return render_template('admin_bingo_no_active_game.html')

    numbers_called = game.get_numbers_called()
    last_number = numbers_called[-1] if numbers_called else None

    # --- Lógica para el bingo pendiente ---
    pending_card_data = None
    if game.status == 'paused' and game.pending_bingo_card_data:
        pending_card_data = json.loads(game.pending_bingo_card_data)

    return render_template('admin_bingo_panel.html',
                           game=game, # Pasamos el objeto de juego completo
                           numbers_called=numbers_called,
                           last_number=last_number,
                           pending_card_data=pending_card_data)

@app.route('/admin/bingo/call_number', methods=['POST'])
@login_required
@roles_required("admin")
def call_bingo_number():
    """
    Endpoint para cantar un nuevo número de bingo.
    Selecciona un número aleatorio que no haya sido cantado
    y lo almacena como 'current_calling_number' con su timestamp.
    """
    active_game = GameSession.query.filter_by(status='active').order_by(GameSession.created_at.desc()).first()

    if not active_game:
        return jsonify({'error': 'No hay una partida de bingo activa para cantar números.'}), 400

    # Si ya hay un número en proceso de ser cantado, no permitir cantar otro
    if active_game.current_calling_number is not None:
        # Determinar si el temporizador ya debería haber terminado
        time_elapsed = datetime.now() - active_game.call_start_time
        if time_elapsed.total_seconds() < 10:
            return jsonify({'error': f'Ya se está cantando el número {active_game.current_calling_number}. Espere a que el temporizador termine.'}), 400
        else:
            # Si el temporizador ya terminó, finalizamos la "cantada" y procesamos el número
            # Esto debería ser manejado por el polling del cliente, pero como fallback
            numbers_called = active_game.get_numbers_called()
            if active_game.current_calling_number not in numbers_called:
                numbers_called.append(active_game.current_calling_number)
                active_game.numbers_called = json.dumps(numbers_called) # Siempre ordenado
                active_game.current_calling_number = None
                active_game.call_start_time = None
                db.session.commit()
                return jsonify({
                    'message': f'Número {numbers_called[-1]} revelado (fallback).',
                    'new_number': numbers_called[-1],
                    'all_called_numbers': numbers_called,
                    'is_revealed': True
                })


    numbers_called = active_game.get_numbers_called()
    called_numbers_set = set(numbers_called)
    all_possible_numbers = set(range(1, 76))
    available_numbers = list(all_possible_numbers - called_numbers_set)

    if not available_numbers:
        return jsonify({'error': 'Todos los números ya han sido cantados. ¡Juego terminado!'}), 400

    # Cantar un número aleatorio de los disponibles
    new_number = random.choice(available_numbers)

    # Establecer el número que se está cantando y el tiempo de inicio
    active_game.current_calling_number = new_number
    active_game.call_start_time = datetime.now() # Guarda la hora actual del servidor
    db.session.commit()

    return jsonify({
        'message': f'Temporizador para el número {new_number} iniciado.',
        'new_number': new_number,
        'call_start_time': int(active_game.call_start_time.timestamp() * 1000), # Timestamp en ms
        'all_called_numbers': numbers_called, # Números cantados hasta ahora (sin el nuevo aún)
        'is_revealed': False # Indicador de que no está revelado todavía
    })

@app.route('/admin/bingo/reset_game', methods=['POST'])
@login_required
@roles_required("admin")
def reset_bingo_game():
    """
    Reinicia o inicia una nueva partida de bingo.
    Marca la partida actual como 'finished' y crea una nueva con 'active' status.
    También reinicia current_calling_number y call_start_time.
    """
    try:
        # Finaliza cualquier partida que esté activa o en espera
        GameSession.query.filter(GameSession.status.in_(['active', 'waiting'])).update({
            'status': 'finished',
            'current_calling_number': None, # Reiniciar estos campos
            'call_start_time': None
        })
        db.session.commit()

        # Crea una nueva sesión de juego
        new_game = GameSession(status='active', numbers_called=json.dumps([]))
        db.session.add(new_game)
        db.session.commit()

        return jsonify({'message': f'Nueva partida de bingo iniciada con ID: {new_game.id}.'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error al resetear/iniciar partida de bingo: {e}")
        return jsonify({'error': 'Error interno al iniciar nueva partida.'}), 500


@app.route('/api/get_current_bingo_status')
def get_current_bingo_status():
    """
    Endpoint API para que los clientes obtengan el estado actual del bingo.
    Ahora también informa si el juego ha terminado y quién fue el ganador.
    """
    # Buscamos la última partida, ya sea activa, pausada o recién finalizada
    latest_game = GameSession.query.order_by(GameSession.created_at.desc()).first()

    if not latest_game:
        return jsonify({'status': 'no_game_found'})

    # Si la partida está finalizada
    if latest_game.status == 'finished':
        return jsonify({
            'status': 'finished',
            'game_id': latest_game.id,
            'winner_user_id': latest_game.winner_user_id
        })

    # Si la partida está activa o pausada (lógica que ya tenías)
    if latest_game.status in ['active', 'paused']:
        numbers_called = latest_game.get_numbers_called()
        last_number = numbers_called[-1] if numbers_called else None
        current_calling_number = latest_game.current_calling_number
        call_start_time_timestamp = None
        if latest_game.call_start_time:
            call_start_time_timestamp = int(latest_game.call_start_time.timestamp() * 1000)

        # Tu lógica para manejar el temporizador de 10 segundos
        if current_calling_number is not None and latest_game.call_start_time is not None:
            elapsed_seconds = (datetime.now() - latest_game.call_start_time).total_seconds()
            if elapsed_seconds >= 10:
                if current_calling_number not in numbers_called:
                    numbers_called.append(current_calling_number)
                    latest_game.numbers_called = json.dumps(numbers_called)
                    latest_game.current_calling_number = None
                    latest_game.call_start_time = None
                    db.session.commit()
                last_number = current_calling_number
                current_calling_number = None
                call_start_time_timestamp = None

        return jsonify({
            'status': latest_game.status,
            'numbers_called': numbers_called,
            'last_number': last_number,
            'current_calling_number': current_calling_number,
            'call_start_time_timestamp': call_start_time_timestamp
        })

    # Si es una partida muy vieja o en estado 'waiting'
    return jsonify({
        'status': 'waiting',
        'numbers_called': [],
    })

# --- Â¡NUEVA RUTA Y FUNCIÃ“N PARA EL MENSAJE DE VERIFICACIÃ“N! ---
@app.route('/check-email-for-confirmation')
@anonymous_user_required # Asegura que solo se pueda acceder si no se ha iniciado sesiÃ³n (o se acaba de registrar)
def check_email_for_confirmation():
    flash("Â¡Gracias por registrarte! Hemos enviado un correo electrÃ³nico de confirmaciÃ³n a tu direcciÃ³n. Por favor, revisa tu bandeja de entrada (y la carpeta de spam) para activar tu cuenta.", "success")
    return render_template('check_email.html')

# --- Manejo de Errores Globales ---
@app.errorhandler(404)
def not_found_error(error):
    """Manejador para páginas no encontradas."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Manejador para errores internos del servidor."""
    db.session.rollback()
    return render_template('500.html'), 500 # Asegúrate de tener un 500.html
