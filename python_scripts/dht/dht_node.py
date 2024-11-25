from hashlib import sha256
import socket
import json
import threading
import time

class DHTNode:
    def __init__(self, ip_address, port, user_id):
        self.ip = ip_address
        self.port = port
        self.user_id = user_id
        self.position = self._hash(f"{ip_address}:{port}") % 1024  # 10-bit ring
        self.data_store = {}
        self.finger_table = {}
        self.successor = None
        self.predecessor = None
        
        # Setup socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip_address, port))
        self.running = False

    def _hash(self, key):
        """Hash function for both node positions and data"""
        return int(sha256(str(key).encode()).hexdigest(), 16)

    def start(self):
        """Start the DHT node"""
        self.running = True
        self.listener_thread = threading.Thread(target=self._listen)
        self.listener_thread.daemon = True
        self.listener_thread.start()

    def _listen(self):
        """Listen for incoming DHT messages"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = json.loads(data.decode())
                self._handle_message(message, addr)
            except Exception as e:
                print(f"DHT Node error: {e}")

    def _handle_message(self, message, addr):
        """Handle incoming DHT messages"""
        msg_type = message.get('type')
        if msg_type == 'store':
            self._handle_store(message)
        elif msg_type == 'retrieve':
            self._handle_retrieve(message, addr)
        elif msg_type == 'find_successor':
            self._handle_find_successor(message, addr)

    def store_data(self, key, value):
        """Store data in this node"""
        key_hash = self._hash(key)
        if self._is_responsible_for(key_hash):
            self.data_store[key] = value
            return True
        return False

    def _is_responsible_for(self, key_hash):
        """Check if this node is responsible for a key"""
        if self.successor is None:
            return True
        if self.position < self.successor.position:
            return self.position <= key_hash < self.successor.position
        return (self.position <= key_hash) or (key_hash < self.successor.position)