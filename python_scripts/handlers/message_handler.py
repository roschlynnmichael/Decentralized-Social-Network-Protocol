from cryptography.fernet import Fernet
import base64
from config import Config

class MessageHandler:
    def __init__(self, key=None):
        self.key = Config.ENCRYPTION_KEY
        if not isinstance(self.key, bytes):
            self.key = self.key.encode()
        self.fernet = Fernet(self.key)

    def encrypt_message(self, message):
        encrypted = self.fernet.encrypt(message.encode())
        return base64.b64encode(encrypted).decode()  # Convert to base64 string
    
    def decrypt_message(self, encrypted_message):
        decoded = base64.b64decode(encrypted_message.encode())
        return self.fernet.decrypt(decoded).decode()
    
    def encrypt_file(self, file_content):
        encrypted_data = self.fernet.encrypt(file_content)
        if len(encrypted_data) > Config.MAX_IPFS_LENGTH:
            raise Exception(f"Encrypted file is too large. Maximum length is {Config.MAX_IPFS_LENGTH} bytes.")
        return encrypted_data
    
    def decrypt_file(self, encrypted_data):
        decrypted_data = self.fernet.decrypt(encrypted_data)
        return decrypted_data
    
    def get_key(self):
        return self.key.decode()
