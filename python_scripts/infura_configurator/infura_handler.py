import os
from dotenv import load_dotenv
from web3 import Web3
from web3.providers import LegacyWebSocketProvider
from config import Config
import json
import hashlib
from eth_account.messages import encode_defunct

# Load environment variables
load_dotenv()

class InfuraHandler:
    def __init__(self, app):
        self.project_id = app.config['INFURA_PROJECT_ID']
        self.http_endpoint = app.config['INFURA_HTTP_ENDPOINT']
        self.ws_endpoint = app.config['INFURA_WS_ENDPOINT']

        # Initialize Web3 instances
        self.w3_http = Web3(Web3.HTTPProvider(self.http_endpoint))
        self.w3_ws = Web3(LegacyWebSocketProvider(self.ws_endpoint))

        self.chat_contract = self.w3_http.eth.contract(
            address=Web3.to_checksum_address(app.config['CHAT_CONTRACT_ADDRESS']),
            abi=json.loads(app.config['CHAT_CONTRACT_ABI'])
        )
        self.file_contract = self.w3_http.eth.contract(
            address=Web3.to_checksum_address(app.config['FILE_CONTRACT_ADDRESS']),
            abi=json.loads(app.config['FILE_CONTRACT_ABI'])
        )

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

    def sign_message(self, message):
        message_hash = hashlib.sha256(message.encode()).hexdigest()
        signed_message = self.w3_http.eth.account.sign_message(
            encode_defunct(text=message_hash),
            private_key=Config.ETHEREUM_PRIVATE_KEY
        )
        return signed_message.signature.hex()

    def verify_signature(self, message, signature, address):
        message_hash = hashlib.sha256(message.encode()).hexdigest()
        recovered_address = self.w3_http.eth.account.recover_message(
            encode_defunct(text=message_hash),
            signature=signature
        )
        return recovered_address.lower() == address.lower()

    def send_transaction(self, to_address, value, data=''):
        transaction = {
            'to': to_address,
            'value': value,
            'gas': 21000,  # Standard gas limit for simple transactions
            'gasPrice': self.w3_http.eth.gas_price,
            'nonce': self.w3_http.eth.get_transaction_count(Config.ETHEREUM_ADDRESS),
            'data': data
        }
        signed_txn = self.w3_http.eth.account.sign_transaction(transaction, Config.ETHEREUM_PRIVATE_KEY)
        tx_hash = self.w3_http.eth.send_raw_transaction(signed_txn.rawTransaction)
        return tx_hash.hex()

    def get_transaction_receipt(self, tx_hash):
        return self.w3_http.eth.get_transaction_receipt(tx_hash)

    def cleanup(self):
        if hasattr(self, 'w3_ws'):
            self.w3_ws.provider.disconnect()

    def store_chat_signature(self, chat_id, chat_hash, signature):
        tx = self.chat_contract.functions.storeChatSignature(chat_id, chat_hash, signature).build_transaction({
            'from': Config.ETHEREUM_ADDRESS,
            'nonce': self.w3_http.eth.get_transaction_count(Config.ETHEREUM_ADDRESS),
        })
        signed_tx = self.w3_http.eth.account.sign_transaction(tx, Config.ETHEREUM_PRIVATE_KEY)
        tx_hash = self.w3_http.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3_http.eth.wait_for_transaction_receipt(tx_hash)

    def get_chat_signature(self, chat_id):
        return self.chat_contract.functions.getChatSignature(chat_id).call()

    def store_file_hash(self, file_hash, owner):
        nonce = self.w3_http.eth.get_transaction_count(Config.ETHEREUM_ADDRESS)
        tx = self.file_contract.functions.storeFileHash(file_hash, owner).build_transaction({
            'from': Config.ETHEREUM_ADDRESS,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': self.w3_http.eth.gas_price,
        })
        signed_tx = self.w3_http.eth.account.sign_transaction(tx, Config.ETHEREUM_PRIVATE_KEY)
        
        # Check if 'rawTransaction' exists, otherwise use 'raw_transaction'
        raw_tx = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction
        
        tx_hash = self.w3_http.eth.send_raw_transaction(raw_tx)
        tx_receipt = self.w3_http.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    def get_file_owner(self, file_hash):
        return self.file_contract.functions.getFileOwner(file_hash).call()
