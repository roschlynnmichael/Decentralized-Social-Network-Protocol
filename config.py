import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_PASSWORD = quote('Dsouza@3191')
    SECRET_KEY = os.urandom(32)
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://p2p_user:{DB_PASSWORD}@192.168.8.208:3306/p2p_social_network'
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
    INFURA_HTTP_ENDPOINT = f"https://sepolia.infura.io/v3/{INFURA_PROJECT_ID}"
    INFURA_WS_ENDPOINT = f"wss://sepolia.infura.io/ws/v3/{INFURA_PROJECT_ID}"
    GAS_ENDPOINT = f"https://gas.api.infura.io/v3/{INFURA_PROJECT_ID}"
    ETHEREUM_ADDRESS = '0x939283adDA5c1fD7f14222DFD39Ce907a522D7ff'
    ETHEREUM_PRIVATE_KEY = '0xcb1c615b965bc0c247ec3d16aecb9512467352f9ed559b655019e612a24461e4'

    #AWS EC2 Configuration
    EC2_PUBLIC_IP = '192.168.8.208'
    #NGINX_USERNAME = 'roschlynnmichael'
    #NGINX_PASSWORD = 'Dsouza3191@'
    MAX_IPFS_LENGTH = 250 * 1024 * 1024
    #SESSION_COOKIE_SECURE = True
    #CSRF_COOKIE_SECURE = True

    #Upload Folder Configuration
    UPLOAD_FOLDER = os.path.join('static', 'profile_pictures')
    BLOCKED_EXTENSIONS = {
        # Executable files
        'exe', 'msi', 'bat', 'cmd', 'sh', 'bin', 'app',
        # Script files
        'vbs', 'ps1', 'js', 'py', 'php', 'pl', 'rb',
        # System files
        'sys', 'dll', 'reg', 'com',
        # Other potentially dangerous files
        'jar', 'apk', 'deb', 'rpm'
    }

    # Add this for profile pictures
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    
    #FERNET KEY CONFIGURATION
    ENCRYPTION_KEY = b'klMnjhfScy3lsuzmSu5yaxhzeortgmCOBI2XOdaullo='

    CHAT_CONTRACT_ADDRESS = '0x88EE9e049A78db3C4f43064748a568D28e9CE6C7'
    FILE_CONTRACT_ADDRESS = '0xe89ef2ea1A042a6075D739886Db259135FaF618f'
    
    CHAT_CONTRACT_ABI = '''
    [
        {
            "inputs": [
                {
                    "internalType": "string",
                    "name": "chatId",
                    "type": "string"
                },
                {
                    "internalType": "string",
                    "name": "chatHash",
                    "type": "string"
                },
                {
                    "internalType": "bytes",
                    "name": "signature",
                    "type": "bytes"
                }
            ],
            "name": "storeChatSignature",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "string",
                    "name": "chatId",
                    "type": "string"
                }
            ],
            "name": "getChatSignature",
            "outputs": [
                {
                    "internalType": "bytes",
                    "name": "",
                    "type": "bytes"
                }
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    '''
    
    FILE_CONTRACT_ABI = '''
    [
        {
            "inputs": [
                {
                    "internalType": "string",
                    "name": "fileHash",
                    "type": "string"
                },
                {
                    "internalType": "address",
                    "name": "owner",
                    "type": "address"
                }
            ],
            "name": "storeFileHash",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "string",
                    "name": "fileHash",
                    "type": "string"
                }
            ],
            "name": "getFileOwner",
            "outputs": [
                {
                    "internalType": "address",
                    "name": "",
                    "type": "address"
                }
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    '''
