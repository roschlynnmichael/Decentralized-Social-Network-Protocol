from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from python_scripts.sql_models.models import db, User, FriendRequest
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import smtplib
import random
import string
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit
import requests
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from urllib.parse import quote
from dotenv import load_dotenv
from python_scripts.eth_account_maker.eth_account_generator import generate_eth_address
from sqlalchemy_utils import database_exists, create_database
from datetime import datetime

load_dotenv()

# SocketIO Setup
socketio = SocketIO()

# Flask Application Setup
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object('config.Config')

mail = Mail(app)

# Login Manager Setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configuration for mail server, serializer and SQLAlchemy
db.init_app(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# IPFS API endpoint
IPFS_API = f'http://{Config.EC2_PUBLIC_IP}:8080/api/v0'

def create_database_if_not_exists(app):
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    if not database_exists(engine.url):
        create_database(engine.url)
    print(f"Database {engine.url.database} {'exists' if database_exists(engine.url) else 'created'}")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

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
    
    # Generate Ethereum address
    eth_address, eth_private_key = generate_eth_address()

    user = User(username=username, email=email, eth_address=eth_address)
    user.set_password(password)
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
            "eth_address": eth_address
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

@app.route('/send_friend_request', methods=['POST'])
@login_required
def send_friend_request():
    data = request.json
    receiver_username = data.get('receiver_username')
    receiver = User.query.filter_by(username=receiver_username).first()

    if not receiver:
        return jsonify({"error": "User not found."}), 404
    
    if receiver == current_user:
        return jsonify({"error": "You cannot send a friend request to yourself."}), 400
    
    # Check if they are already friends
    if current_user.friends.filter_by(id=receiver.id).first():
        return jsonify({"error": "You are already friends with this user."}), 400
    
    # Check for existing friend requests in both directions
    existing_request = FriendRequest.query.filter(
        ((FriendRequest.sender == current_user) & (FriendRequest.receiver == receiver)) |
        ((FriendRequest.sender == receiver) & (FriendRequest.receiver == current_user))
    ).first()

    if existing_request:
        if existing_request.status == 'pending':
            if existing_request.sender == current_user:
                return jsonify({"error": "You have already sent a friend request to this user."}), 400
            else:
                return jsonify({"error": "This user has already sent you a friend request. Check your pending requests."}), 400
        elif existing_request.status == 'accepted':
            return jsonify({"error": "You are already friends with this user."}), 400
        elif existing_request.status == 'rejected':
            # If a previous request was rejected, we can allow a new request
            existing_request.status = 'pending'
            existing_request.sender = current_user
            existing_request.receiver = receiver
            existing_request.timestamp = datetime.utcnow()
            db.session.commit()
            return jsonify({"message": "Friend request sent successfully."}), 200
    
    # If no existing request, create a new one
    new_request = FriendRequest(sender=current_user, receiver=receiver)
    db.session.add(new_request)
    db.session.commit()

    return jsonify({"message": "Friend request sent successfully."}), 200

@app.route('/accept_friend_request/<int:request_id>', methods=['POST'])
@login_required
def accept_friend_request(request_id):
    friend_request = FriendRequest.query.get_or_404(request_id)
    
    if friend_request.receiver != current_user:
        return jsonify({"error": "Unauthorized"}), 403
    
    if friend_request.status != 'pending':
        return jsonify({"error": "This request has already been processed"}), 400
    
    friend_request.status = 'accepted'
    
    # Add each user to the other's friends list
    current_user.friends.append(friend_request.sender)
    friend_request.sender.friends.append(current_user)
    
    db.session.commit()
    
    return jsonify({"message": "Friend request accepted"}), 200

@app.route('/reject_friend_request/<int:request_id>', methods=['POST'])
@login_required
def reject_friend_request(request_id):
    friend_request = FriendRequest.query.get_or_404(request_id)
    
    if friend_request.receiver != current_user:
        return jsonify({"error": "Unauthorized"}), 403
    
    if friend_request.status != 'pending':
        return jsonify({"error": "This request has already been processed"}), 400
    
    friend_request.status = 'rejected'
    db.session.commit()
    
    return jsonify({"message": "Friend request rejected"}), 200

@app.route('/friend_requests', methods=['GET'])
@login_required
def get_friend_requests():
    pending_requests = FriendRequest.query.filter_by(receiver=current_user, status='pending').all()
    requests_data = [{
        'id': req.id,
        'sender_username': req.sender.username,
        'timestamp': req.timestamp
    } for req in pending_requests]
    return jsonify(requests_data), 200

@app.route('/friends', methods=['GET'])
@login_required
def get_friends():
    friends = current_user.friends.all()
    friends_data = [{
        'id': friend.id,
        'username': friend.username,
        'eth_address': friend.eth_address
    } for friend in friends]
    return jsonify(friends_data), 200

@app.route('/friend_requests/<int:request_id>', methods=['DELETE'])
@login_required
def delete_friend_request(request_id):
    friend_request = FriendRequest.query.get_or_404(request_id)
    if friend_request.receiver != current_user:
        return jsonify({"error": "Unauthorized access."}), 403

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
    pending_requests = FriendRequest.query.filter_by(receiver = current_user, status = 'pending').all()
    friends = current_user.friends.all()
    return render_template('dashboard.html', pending_requests=pending_requests, friends=friends)

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

@app.route('/api/current_user', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({
        'username': current_user.username,
        'email': current_user.email
    }), 200

@app.route('/api/search_users', methods=['GET'])
@login_required
def search_users():
    query = request.args.get('query', '')
    if len(query) < 3:
        return jsonify([])
    
    users = User.query.filter(User.username.ilike(f'%{query}%')).limit(10).all()
    return jsonify([{'id': user.id, 'username': user.username} for user in users])

@app.route('/api/send_friend_request', methods=['POST'])
@login_required
def api_send_friend_request():
    data = request.json
    receiver_id = data.get('receiver_id')
    receiver = User.query.get(receiver_id)

    if not receiver:
        return jsonify({"error": "User not found."}), 404
    if receiver == current_user:
        return jsonify({"error": "You cannot send a friend request to yourself."}), 400

    # Check if they are already friends
    if receiver in current_user.friends:
        return jsonify({"error": "You are already friends with this user."}), 400

    existing_request = FriendRequest.query.filter(
        ((FriendRequest.sender == current_user) & (FriendRequest.receiver == receiver)) |
        ((FriendRequest.sender == receiver) & (FriendRequest.receiver == current_user)),
        FriendRequest.status == 'pending'
    ).first()

    if existing_request:
        if existing_request.sender == current_user:
            return jsonify({"error": "Friend request already sent."}), 400
        else:
            return jsonify({"error": "This user has already sent you a friend request."}), 400

    new_request = FriendRequest(sender=current_user, receiver=receiver)
    db.session.add(new_request)
    db.session.commit()

    return jsonify({"message": "Friend request sent successfully."}), 200

@app.route('/api/chats', methods=['GET'])
@login_required
def get_chats():
    # Implement logic to fetch and return user's chats
    # For now, you can return an empty list
    return jsonify([])

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    with app.app_context():
        create_database_if_not_exists(app)
        db.create_all()
    socketio.init_app(app)
    socketio.run(app, debug=True)
