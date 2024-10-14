import os
from dotenv import load_dotenv
from python_scripts.handlers.message_handler import MessageHandler
from python_scripts.handlers.p2p_socket_handler import P2PSocketHandler
from python_scripts.handlers.blockchain_handler import BlockchainHandler
from python_scripts.handlers.ipfs_handler import IPFSHandler
from web3 import Web3
from web3.providers import LegacyWebSocketProvider
from config import Config
import json

# Load environment variables
load_dotenv()

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(base_dir, 'json_files', 'UserRegistry.json')

class InfuraHandler:
    def __init__(self, app):
        self.project_id = app.config['INFURA_PROJECT_ID']
        self.http_endpoint = app.config['INFURA_HTTP_ENDPOINT']
        self.gas_endpoint = app.config['INFURA_GAS_ENDPOINT']
        self.ws_endpoint = app.config['INFURA_WS_ENDPOINT']

        if not self.project_id:
            raise ValueError("INFURA_PROJECT_ID must be set in the environment variables or config")

        # Initialize Web3 instances
        self.w3_http = Web3(Web3.HTTPProvider(self.http_endpoint))
        self.w3_ws = Web3(LegacyWebSocketProvider(self.ws_endpoint))

        # Initialize other handlers
        encryption_key = app.config.get('ENCRYPTION_KEY')
        self.message_handler = MessageHandler(key=encryption_key)
        
        # If no encryption key was provided, save the generated one
        if not encryption_key:
            app.config['ENCRYPTION_KEY'] = self.message_handler.get_key()
        
        self.p2p_socket = P2PSocketHandler(app)
        self.ipfs = IPFSHandler()

        # Initialize BlockchainHandler
        self.blockchain = BlockchainHandler(self.project_id)

        # Load your contract ABI and address
        with open(json_path, 'r') as f:
            contract_json = json.load(f)
        self.contract_address = Web3.to_checksum_address('0xd9145CCE52D386f254917e481eB44e9943F39138')
        self.contract = self.w3_ws.eth.contract(address=self.contract_address, abi=contract_json['abi'])

    def initialize(self):
        if not self.blockchain.check_https_connection():
            print("Warning: Unable to connect to Ethereum network via HTTPS")
        if not self.blockchain.check_ws_connection():
            print("Warning: Unable to connect to Ethereum network via WebSocket")

    def send_message(self, sender, recipient, message):
        encrypted_message = self.message_handler.encrypt_message(message)
        self.p2p_socket.send_message(sender, recipient, encrypted_message)
        self.blockchain.store_user_interaction(sender, recipient, 'message')

    def receive_message(self, sender, encrypted_message):
        return self.message_handler.decrypt_message(encrypted_message)

    def upload_file_to_ipfs(self, file_path):
        file_hash = self.ipfs.add_file(file_path)
        if file_hash:
            self.blockchain.store_user_interaction(file_hash, 'file_upload')
        return file_hash

    def retrieve_file_from_ipfs(self, file_hash):
        file_content = self.ipfs.get_file(file_hash)
        if file_content:
            if self.blockchain.verify_content_ownership(file_hash):
                return file_content
            else:
                print("Warning: File hash not verified on blockchain")
        return None

    def run(self, app, debug=True):
        self.p2p_socket.run(app, debug=debug)

    def cleanup(self):
        if hasattr(self, 'w3_ws'):
            self.w3_ws.provider.disconnect()
        self.ipfs.close()

    def get_latest_block(self):
        return self.w3_http.eth.get_block('latest')

    def get_gas_price(self):
        return self.w3_http.eth.gas_price

    def estimate_transaction_cost(self, from_address, to_address, value):
        gas_estimate = self.w3_http.eth.estimate_gas({
            'from': from_address,
            'to': to_address,
            'value': value
        })
        gas_price = self.get_gas_price()
        return gas_estimate * gas_price

    def listen_for_new_blocks(self, callback):
        def handle_event(event):
            block = self.w3_ws.eth.get_block(event)
            callback(block)
        
        new_block_filter = self.w3_ws.eth.filter('latest')
        new_block_filter.watch(handle_event)

    def register_user(self, username, eth_address):
        if not eth_address:
            raise ValueError("Ethereum address is required for blockchain registration")
        
        eth_address = Web3.to_checksum_address(eth_address)
        
        # Check if user already exists
        if self.contract.functions.userExists(eth_address).call():
            raise ValueError("User already registered on blockchain")
        
        # Prepare the transaction
        transaction = self.contract.functions.registerUser(username).build_transaction({
            'from': eth_address,
            'gas': 2000000,
            'gasPrice': self.w3_ws.eth.gas_price,
            'nonce': self.w3_ws.eth.get_transaction_count(eth_address),
        })
        
        # In a real-world scenario, you would need to sign this transaction with the user's private key
        # For demonstration, we'll just return the transaction object
        return transaction

    def user_exists(self, eth_address):
        eth_address = Web3.to_checksum_address(eth_address)
        return self.contract.functions.userExists(eth_address).call()

    def get_user(self, eth_address):
        eth_address = Web3.to_checksum_address(eth_address)
        return self.contract.functions.getUser(eth_address).call()
