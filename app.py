from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from python_scripts.sql_models.models import db, User
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
import smtplib
import random
import string
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from python_scripts.infura_configurator.infura_handler import InfuraHandler
from flask_socketio import SocketIO, emit
import requests
import json

# SocketIO Setup
socketio = SocketIO()

# Flask Application Setup
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)

# Login Manager Setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configuration for mail server, serializer and SQLAlchemy
db.init_app(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# IPFS API endpoint
IPFS_API = f'http://{Config.EC2_PUBLIC_IP}:8080/api/v0'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Function to send email
def send_email(subject, body, sender, recipients, password):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
       smtp_server.login(sender, password)
       smtp_server.sendmail(sender, recipients, msg.as_string())
    print("Message sent!")

# Function to generate verification code
def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({"Error": "Username already exists"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"Error": "Email already exists"}), 400
    
    hashed_password = generate_password_hash(password)
    user = User(username=username, email=email, password=hashed_password)
    db.session.add(user)
    db.session.commit()

    token = serializer.dumps(email, salt='email-confirm-salt')
    confirm_url = url_for('activate', token=token, _external=True)
    
    subject = "Confirm Your Email"
    body = f"Please click the following link to confirm your email: {confirm_url}"
    sender = app.config['MAIL_USERNAME']
    recipients = [email]
    password = app.config['MAIL_PASSWORD']

    try:
        send_email(subject, body, sender, recipients, password)
        return jsonify({
            "message": "Registration successful. Please check your email for activation link.",
        }), 201
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        db.session.delete(user)
        db.session.commit()
        return jsonify({
            "error": "Registration failed. Unable to send activation email. Please try again later.",
        }), 500

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'GET':
        return render_template('reset_password_request.html')
    
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    if user:
        token = serializer.dumps(user.email, salt='password-reset-salt')
        reset_url = url_for('reset_password', token=token, _external=True)
        subject = "Password Reset Request"
        body = f"Click the following link to reset your password: {reset_url}"
        send_email(subject, body, app.config['MAIL_USERNAME'], [user.email], app.config['MAIL_PASSWORD'])
        return jsonify({"message": "Password reset link sent to your email."}), 200
    return jsonify({"error": "No account found with that email address."}), 404

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'GET':
        return render_template('reset_password.html', token=token)
    
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except (SignatureExpired, BadSignature):
        return jsonify({"error": "The password reset link is invalid or has expired."}), 400

    new_password = request.json.get('new_password')
    user = User.query.filter_by(email=email).first()
    if user:
        user.password = generate_password_hash(new_password)
        db.session.commit()
        return jsonify({"message": "Your password has been updated."}), 200
    return jsonify({"error": "User not found."}), 404

@app.route('/activate/<token>', methods=['GET'])
def activate(token):
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=3600)
    except SignatureExpired:
        return jsonify({"error": "The confirmation link has expired."}), 400
    except BadSignature:
        return jsonify({"error": "The confirmation link is invalid."}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        if not user.is_active:
            user.is_active = True
            db.session.commit()
            return jsonify({"message": "Your account has been activated successfully."}), 200
        else:
            return jsonify({"message": "Your account is already activated."}), 200
    else:
        return jsonify({"error": "No user found with that email address."}), 404

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.json
    identifier = data.get('identifier')
    password = data.get('password')

    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()

    if not user:
        return jsonify({"error": "No account found with that username or email."}), 404
    
    if not user.is_active:
        return jsonify({"error": "Account not activated. Please check your email for the activation link."}), 403

    if not user.check_password(password):
        return jsonify({"error": "Incorrect password."}), 401

    login_user(user)
    return jsonify({"message": "Login successful!", "redirect": url_for('dashboard')}), 200

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/chats')
@login_required
def get_chats():
    # TODO: Implement fetching user's chats from the database
    # For now, return dummy data
    chats = [
        {'id': 1, 'name': 'Chat 1', 'last_message': 'Hello'},
        {'id': 2, 'name': 'Chat 2', 'last_message': 'How are you?'},
    ]
    return jsonify(chats)

@app.route('/api/chat/<int:chat_id>/messages')
@login_required
def get_chat_messages(chat_id):
    # TODO: Implement fetching messages from IPFS using the chat_id
    # For now, return dummy data
    messages = [
        {'sender': 'User1', 'content': 'Hello'},
        {'sender': 'User2', 'content': 'Hi there!'},
    ]
    return jsonify(messages)

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.json
    chat_id = data['chat_id']
    content = data['content']
    
    message = {
        'sender': current_user.username,
        'content': content,
        'chat_id': chat_id
    }
    
    # Add message to IPFS
    files = {'file': json.dumps(message)}
    response = requests.post(f'{IPFS_API}/add', files=files)
    ipfs_hash = response.json()['Hash']
    
    # TODO: Update your database with the new IPFS hash
    
    # Broadcast the new message to all connected clients
    socketio.emit('new_message', message)
    
    return jsonify({'success': True, 'ipfs_hash': ipfs_hash})

@app.route('/api/search_friends')
@login_required
def search_friends():
    query = request.args.get('query', '')
    # TODO: Implement searching for users in your database
    # For now, return dummy data
    results = [
        {'id': 1, 'username': 'user1'},
        {'id': 2, 'username': 'user2'},
    ]
    return jsonify(results)

@app.route('/api/start_chat', methods=['POST'])
@login_required
def start_chat():
    data = request.json
    user_id = data.get('user_id')
    # TODO: Implement creating a new chat in your database
    # For now, return dummy data
    new_chat = {
        'id': 3,
        'name': f'Chat with User {user_id}',
        'last_message': 'New chat started'
    }
    return jsonify({'success': True, 'chat': new_chat})

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.init_app(app)
    socketio.run(app, debug=True)