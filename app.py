from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from python_scripts.sql_models.models import db, User, FriendRequest
from python_scripts.handlers.p2p_socket_handler import P2PSocketHandler
from python_scripts.handlers.message_handler import MessageHandler
from python_scripts.handlers.ipfs_handler import IPFSHandler
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from python_scripts.infura_configurator.infura_handler import InfuraHandler
import smtplib
import random
import string
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
from flask_socketio import SocketIO, emit, join_room, send, leave_room
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
from werkzeug.utils import secure_filename
import logging
import tempfile
from python_scripts.infura_configurator.infura_handler import InfuraHandler
from web3 import Web3
import hashlib
import time

load_dotenv()

# Flask Application Setup
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object('config.Config')

# SocketIO Setup
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   manage_session=False, 
                   logger=True, 
                   engineio_logger=True)

mail = Mail(app)

#IPFS Setup
ipfs_handler = IPFSHandler()

#Message Handler Setup
message_handler = MessageHandler()

# Login Manager Setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

#Infura Handler Setup
infura_handler = InfuraHandler(app)

# Get allowed extensions and upload folder from config
def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    
    # For profile picture uploads
    if request.endpoint == 'upload_profile_picture':
        return ext in app.config['ALLOWED_EXTENSIONS']
    
    # For file sharing in chat
    return ext not in app.config['BLOCKED_EXTENSIONS']

# Configuration for mail server, serializer and SQLAlchemy
db.init_app(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# IPFS API endpoint
IPFS_API = f'http://{Config.EC2_PUBLIC_IP}:8080/api/v0'

def create_database_if_not_exists(app):
    try:
        engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        if not database_exists(engine.url):
            create_database(engine.url)
        print(f"Database {engine.url.database} {'exists' if database_exists(engine.url) else 'created'}")
        return True
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        return False

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
        return jsonify({"error": "Username already exists"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400
    
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
    
    # Emit a socket event to notify the sender and receiver
    friend = friend_request.sender
    socketio.emit('friend_request_accepted', {
        'friend_id': friend.id,
        'friend_username': friend.username,
        'friend_profile_picture': friend.profile_picture
    }, room=current_user.id)
    socketio.emit('friend_request_accepted', {
        'friend_id': current_user.id,
        'friend_username': current_user.username,
        'friend_profile_picture': current_user.profile_picture
    }, room=friend.id)

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

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))
    
@app.errorhandler(404)
def not_found_error(error):
    if current_user.is_authenticated:
        return render_template('404.html'), 404
    return redirect(url_for('login'))

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if request.is_xhr:
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500
    return render_template('500.html'), 500

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
    
    if user and user.check_password(password):
        login_user(user)
        P2PSocketHandler.start_user_socket_server(user)
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
    return jsonify([{'id': user.id, 'username': user.username, 'profile_picture': user.profile_picture if user.profile_picture else 'default.png'} for user in users])

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

@app.route('/upload_profile_picture', methods=['POST'])
@login_required
def upload_profile_picture():
    if 'profile_picture' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['profile_picture']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower()
            new_filename = f"user_{current_user.id}.{file_extension}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(file_path)
            
            # Update user's profile picture in the database
            current_user.profile_picture = new_filename
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Profile picture updated successfully",
                "filename": new_filename
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error uploading profile picture: {str(e)}")
            return jsonify({
                "success": False,
                "error": "An error occurred while uploading the profile picture"
            }), 500
    
    return jsonify({
        "success": False,
        "error": "File type not allowed"
    }), 400

@app.route('/remove_profile_picture', methods=['POST'])
@login_required
def remove_profile_picture():
    try:
        # Remove the current profile picture file
        if current_user.profile_picture != 'default.png':
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_picture)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Set the user's profile picture to the default
        current_user.profile_picture = 'default.png'
        db.session.commit()
        
        return jsonify({"message": "Profile picture removed successfully"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error removing profile picture: {str(e)}")
        return jsonify({"error": "An error occurred while removing the profile picture"}), 500

@app.route('/get_profile_picture/<int:user_id>')
def get_profile_picture(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({"profile_picture": user.profile_picture}), 200

@app.route('/api/friends', methods=['GET'])
@login_required
def get_friends():
    friend_requests = FriendRequest.query.filter(
        ((FriendRequest.sender_id == current_user.id) | (FriendRequest.receiver_id == current_user.id)) &
        (FriendRequest.status == 'accepted')
    ).all()
    friends = []
    for request in friend_requests:
        friend = request.receiver if request.sender_id == current_user.id else request.sender
        friends.append({
            'friend_id': friend.id,
            'friend_username': friend.username,
            'friend_profile_picture': friend.profile_picture
        })
    return jsonify(friends)

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

@app.route('/api/get_friend_socket_info/<int:friend_id>')
@login_required
def get_friend_socket_info(friend_id):
    friend = User.query.get_or_404(friend_id)
    return jsonify({
        'host': friend.socket_host,
        'port': friend.socket_port
    })

@app.route('/api/chat_history/<int:friend_id>')
@login_required
def get_chat_history(friend_id):
    try:
        chat_history_hash = current_user.chat_history_hash
        if not chat_history_hash:
            return jsonify({'messages': []}), 200

        encrypted_history = ipfs_handler.get_content(chat_history_hash)
        if not encrypted_history:
            return jsonify({'messages': []}), 200

        try:
            chat_history = json.loads(encrypted_history)
        except json.JSONDecodeError:
            app.logger.error(f"Invalid JSON in chat history for user {current_user.id}")
            return jsonify({'messages': [], 'error': 'Invalid chat history format'}), 200

        # Filter messages for the specific friend
        filtered_history = [
            msg for msg in chat_history 
            if (msg['sender_id'] == current_user.id and msg['friend_id'] == friend_id) or 
               (msg['sender_id'] == friend_id and msg['friend_id'] == current_user.id)
        ]

        # Decrypt message content
        for msg in filtered_history:
            try:
                msg['content'] = message_handler.decrypt_message(msg['content'])
            except Exception as e:
                app.logger.error(f"Error decrypting message: {str(e)}")
                msg['content'] = "Error: Could not decrypt message"

        return jsonify({'messages': filtered_history}), 200
    except Exception as e:
        app.logger.error(f"Error retrieving chat history: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while retrieving chat history."}), 500

@socketio.on('connect')
def handle_connect():
    app.logger.debug(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    app.logger.debug(f"Client disconnected: {request.sid}")

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    app.logger.debug(f"Client {request.sid} joined room: {room}")

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    app.logger.debug(f"Client {request.sid} left room: {room}")

@socketio.on('message')
def handle_message(data):
    try:
        room = data['room']
        content = data['content']
        sender_id = data['sender_id']
        recipient_id = data['recipient_id']
        timestamp = data['timestamp']

        # Store message in database/IPFS if needed
        message_data = {
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'content': content,
            'timestamp': timestamp,
            'room': room
        }

        # Emit to the room (both sender and recipient will receive it)
        emit('new_message', message_data, room=room)
        
        app.logger.debug(f"Message sent in room {room}: {message_data}")
    except Exception as e:
        app.logger.error(f"Error handling message: {str(e)}")

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.json
    friend_id = data.get('friend_id')
    message_content = data.get('message')
    room = data.get('room')
    timestamp = data.get('timestamp')
    
    try:
        # Store message for both users regardless of active chat
        for user in [current_user, User.query.get(friend_id)]:
            chat_history = []
            if user.chat_history_hash:
                try:
                    encrypted_history = ipfs_handler.get_content(user.chat_history_hash)
                    chat_history = json.loads(encrypted_history)
                except (json.JSONDecodeError, Exception) as e:
                    app.logger.error(f"Error loading chat history for user {user.id}: {str(e)}")
                    chat_history = []

            # Encrypt the message
            encrypted_message = message_handler.encrypt_message(message_content)

            # Add new message to history
            new_message = {
                'sender_id': current_user.id,
                'friend_id': friend_id,
                'content': encrypted_message,
                'timestamp': timestamp,
                'cleared_by': []
            }
            
            chat_history.append(new_message)
            
            # Store updated history in IPFS
            updated_history_hash = ipfs_handler.add_content(json.dumps(chat_history))
            user.chat_history_hash = updated_history_hash

        db.session.commit()

        # Emit the message through socket
        socketio.emit('new_message', {
            'sender_id': current_user.id,
            'recipient_id': friend_id,
            'content': message_content,
            'timestamp': timestamp,
            'room': room
        }, room=room)

        return jsonify({"success": True, "message": "Message sent and stored successfully"}), 200

    except Exception as e:
        app.logger.error(f"Error in send_message: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/store_message', methods=['POST'])
@login_required
def store_message():
    data = request.json
    friend_id = data.get('friend_id')
    message = data.get('message')
    
    # Store message in IPFS
    ipfs_handler = IPFSHandler()
    ipfs_hash = ipfs_handler.add_content(message)
    
    # Here you might want to store the IPFS hash in your database to keep track of the chat history
    
    return jsonify({'status': 'success', 'ipfs_hash': ipfs_hash})

@app.route('/api/clear_chat/<int:friend_id>', methods=['POST'])
@login_required
def clear_chat(friend_id):
    try:
        # Get the current user's chat history
        if current_user.chat_history_hash:
            current_user_history = json.loads(ipfs_handler.get_content(current_user.chat_history_hash))
        else:
            current_user_history = []

        # Remove messages with the specific friend
        current_user_history = [msg for msg in current_user_history 
                                if not (msg['friend_id'] == friend_id or msg['sender_id'] == friend_id)]

        # Store the updated history back to IPFS
        new_history_hash = ipfs_handler.add_content(json.dumps(current_user_history))

        # Update the current user's chat history hash in the database
        current_user.chat_history_hash = new_history_hash

        db.session.commit()

        return jsonify({"success": True, "message": "Chat history cleared successfully."}), 200
    except Exception as e:
        app.logger.error(f"Error clearing chat history: {str(e)}")
        return jsonify({"success": False, "error": "An error occurred while clearing chat history."}), 500

@app.route('/api/share_file', methods=['POST'])
@login_required
def share_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400

        # Read and encrypt the file content
        file_content = file.read()
        encrypted_content = message_handler.encrypt_file(file_content)

        # Upload to IPFS
        ipfs_hash = ipfs_handler.add_content(encrypted_content)
        
        # Store file hash on blockchain using Infura
        try:
            tx_receipt = infura_handler.store_file_hash(
                ipfs_hash, 
                current_user.eth_address
            )
            tx_hash = tx_receipt['transactionHash'].hex()
            app.logger.info(f"File hash stored on blockchain. Transaction hash: {tx_hash}")
        except Exception as e:
            app.logger.error(f"Blockchain storage error: {str(e)}")
            tx_hash = None

        file_data = {
            'ipfs_hash': ipfs_hash,
            'filename': secure_filename(file.filename),
            'tx_hash': tx_hash
        }

        return jsonify({
            'success': True,
            'file_link': f'/api/download_file/{ipfs_hash}/{secure_filename(file.filename)}',
            'file_data': file_data,
            'tx_hash': tx_hash  # Include transaction hash in response
        })

    except Exception as e:
        app.logger.error(f"Error sharing file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download_file/<ipfs_hash>/<filename>', methods=['GET'])
@login_required
def download_file(ipfs_hash, filename):
    try:
        encrypted_data = ipfs_handler.get_content(ipfs_hash)
        decrypted_data = message_handler.decrypt_file(encrypted_data)
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{filename}') as temp_file:
            temp_file.write(decrypted_data)
            temp_path = temp_file.name

        # Send the file
        return send_file(temp_path, as_attachment=True, download_name=filename)

    except Exception as e:
        app.logger.error(f"Error downloading file: {str(e)}")
        return jsonify({"error": f"An error occurred while downloading the file: {str(e)}"}), 500

    finally:
        # Clean up the temporary file
        if 'temp_path' in locals():
            try:
                os.unlink(temp_path)
            except Exception as e:
                app.logger.error(f"Error removing temporary file: {str(e)}")

@app.route('/api/sign_chat/<int:friend_id>', methods=['POST'])
@login_required
def sign_chat(friend_id):
    chat_id = f"{current_user.id}_{friend_id}"
    chat_history = json.loads(ipfs_handler.get_content(current_user.chat_history_hash))
    chat_hash = hashlib.sha256(json.dumps(chat_history).encode()).hexdigest()
    signature = infura_handler.sign_message(chat_hash)
    return jsonify({"signature": signature}), 200

@app.route('/api/verify_chat/<int:friend_id>', methods=['POST'])
@login_required
def verify_chat(friend_id):
    data = request.json
    chat_id = f"{current_user.id}_{friend_id}"
    chat_history = json.loads(ipfs_handler.get_content(current_user.chat_history_hash))
    chat_hash = hashlib.sha256(json.dumps(chat_history).encode()).hexdigest()
    is_verified = infura_handler.verify_signature(chat_hash, data['signature'], current_user.eth_address)
    return jsonify({"verified": is_verified}), 200

@app.route('/api/send_eth', methods=['POST'])
@login_required
def send_eth():
    data = request.json
    to_address = data['to_address']
    value = Web3.to_wei(data['amount'], 'ether')
    tx_hash = infura_handler.send_transaction(to_address, value)
    return jsonify({"transaction_hash": tx_hash}), 200

@app.route('/api/verify_file/<ipfs_hash>', methods=['GET'])
@login_required
def verify_file(ipfs_hash):
    try:
        owner_address = infura_handler.get_file_owner(ipfs_hash)
        is_verified = owner_address.lower() == current_user.eth_address.lower()
        return jsonify({"verified": is_verified, "owner": owner_address}), 200
    except Exception as e:
        app.logger.error(f"Error verifying file: {str(e)}")
        return jsonify({"error": f"An error occurred while verifying the file: {str(e)}"}), 500

@app.route('/transaction_history')
@login_required
def transaction_history():
    # Fetch transaction history from Infura
    # This is a placeholder - you'll need to implement the actual fetching logic
    transactions = infura_handler.get_transaction_history(current_user.eth_address)
    return render_template('transaction_history.html', transactions=transactions)

@app.route('/api/blockchain_status', methods=['GET'])
def blockchain_status():
    try:
        # Check if we can connect to the Ethereum network
        latest_block = infura_handler.w3_http.eth.get_block('latest')
        return jsonify({"connected": True, "latest_block": latest_block.number}), 200
    except Exception as e:
        app.logger.error(f"Error checking blockchain status: {str(e)}")
        return jsonify({"connected": False, "error": str(e)}), 500

@socketio.on('typing')
def handle_typing(data):
    room = data.get('room')
    user_id = data.get('user_id')
    emit('user_typing', {'user_id': user_id}, room=room)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    room = data.get('room')
    user_id = data.get('user_id')
    emit('user_stop_typing', {'user_id': user_id}, room=room)

@socketio.on('message_reaction')
def handle_reaction(data):
    room = data.get('room')
    message_id = data.get('message_id')
    reaction = data.get('reaction')
    user_id = data.get('user_id')
    
    emit('reaction_update', {
        'message_id': message_id,
        'reaction': reaction,
        'user_id': user_id
    }, room=room)

#if __name__ == '__main__':
#    with app.app_context():
#        create_database_if_not_exists(app)
#        db.create_all()
   # socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
