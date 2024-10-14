import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

class Config:
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

    #Infura Configuration
    INFURA_PROJECT_ID = 'df4d18360ebc45049c9bc3820d1f00cf'
    INFURA_HTTP_ENDPOINT = f"https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}"
    INFURA_GAS_ENDPOINT = f"https://gas.api.infura.io/v3/{INFURA_PROJECT_ID}"
    INFURA_WS_ENDPOINT = f"wss://mainnet.infura.io/ws/v3/{INFURA_PROJECT_ID}"

    #AWS EC2 Configuration
    EC2_PUBLIC_IP = '13.59.2.130'
