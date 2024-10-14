from cryptography.fernet import Fernet

class MessageHandler:
    def __init__(self, key=None):
        if key is None:
            self.key = Fernet.generate_key()
        else:
            self.key = key if isinstance(key, bytes) else key.encode()
        self.fernet = Fernet(self.key)

    def encrypt_message(self, message):
        return self.fernet.encrypt(message.encode())
    
    def decrypt_message(self, encrypted_message):
        return self.fernet.decrypt(encrypted_message).decode()
    
    def send_p2p_message(self, sender, receiver, message):
        encrypted_message = self.encrypt_message(message)
        return encrypted_message

    def receive_p2p_message(self, sender, receiver, message):
        decrypted_message = self.decrypt_message(message)
        return decrypted_message

    def get_key(self):
        return self.key.decode()
