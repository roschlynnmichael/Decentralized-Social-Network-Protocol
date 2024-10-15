#p2p_user
#Dsouza@3191
#rootlocalhost:roschlynnmichael
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Increased length to 255
    eth_address = db.Column(db.String(42), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    profile_picture = db.Column(db.String(255), default='default.png', nullable=True)

    friends = db.relationship(
        'User',
        secondary = 'friendships',
        primaryjoin = ('friendships.c.user_id == User.id'),
        secondaryjoin = ('friendships.c.friend_id == User.id'),
        backref = db.backref('friended_by', lazy = 'dynamic'),
        lazy = 'dynamic'
    )

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.username}>'
    
class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    status = db.Column(db.String(20), default = 'pending')
    timestamp = db.Column(db.DateTime, default = datetime.utcnow)

    sender = db.relationship('User', foreign_keys = [sender_id], backref = 'sent_requests')
    receiver = db.relationship('User', foreign_keys = [receiver_id], backref = 'received_requests')

friendships = db.Table(
    'friendships',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key = True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key = True)
)
