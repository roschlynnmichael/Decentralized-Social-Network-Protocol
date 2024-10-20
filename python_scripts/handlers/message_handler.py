from cryptography.fernet import Fernet
import base64

class MessageHandler:
    def __init__(self, key=None):
        if key is None:
            self.key = Fernet.generate_key()
        else:
            self.key = key if isinstance(key, bytes) else key.encode()
        self.fernet = Fernet(self.key)

    def encrypt_message(self, message):
        encrypted = self.fernet.encrypt(message.encode())
        return base64.b64encode(encrypted).decode()  # Convert to base64 string
    
    def decrypt_message(self, encrypted_message):
        decoded = base64.b64decode(encrypted_message.encode())
        return self.fernet.decrypt(decoded).decode()
    
    def get_key(self):
        return self.key.decode()
