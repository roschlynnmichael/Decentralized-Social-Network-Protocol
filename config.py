import os
from urllib.parse import quote

class Config:
    #SQL Configuration
    DB_PASSWORD = quote('Dsouza@3191')
    SECRET_KEY = os.urandom(32)
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://p2p_user:{DB_PASSWORD}@localhost:3306/p2p_social_network'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    #Mail Server Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'cnetworks361@gmail.com'
    MAIL_PASSWORD = 'etap vwie zggy iruk'
