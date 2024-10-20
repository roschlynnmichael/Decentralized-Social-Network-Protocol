import os
from dotenv import load_dotenv
from web3 import Web3
from web3.providers import LegacyWebSocketProvider
from config import Config
import json
import hashlib
from eth_account.messages import encode_defunct
import time

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
        tx_hash = self.w3_http.eth.send_raw_transaction(signed_txn.raw_transaction)
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

    def estimate_gas(self, transaction):
        return self.w3_http.eth.estimate_gas(transaction)

    def store_file_hash(self, file_hash, owner, max_attempts=5):
        for attempt in range(max_attempts):
            try:
                nonce = self.w3_http.eth.get_transaction_count(Config.ETHEREUM_ADDRESS)
                gas_price = self.w3_http.eth.gas_price
                
                # Estimate gas
                gas_estimate = self.file_contract.functions.storeFileHash(file_hash, owner).estimate_gas({
                    'from': Config.ETHEREUM_ADDRESS,
                    'nonce': nonce,
                    'gasPrice': gas_price,
                })
                
                # Add some buffer to the gas estimate
                gas_limit = int(gas_estimate * 1.2)

                tx = self.file_contract.functions.storeFileHash(file_hash, owner).build_transaction({
                    'from': Config.ETHEREUM_ADDRESS,
                    'nonce': nonce,
                    'gasPrice': gas_price,
                    'gas': gas_limit,
                })
                
                signed_tx = self.w3_http.eth.account.sign_transaction(tx, Config.ETHEREUM_PRIVATE_KEY)
                tx_hash = self.w3_http.eth.send_raw_transaction(signed_tx.raw_transaction)
                tx_receipt = self.w3_http.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                return tx_receipt
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_attempts - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff

    def get_file_owner(self, file_hash):
        try:
            return self.file_contract.functions.getFileOwner(file_hash).call()
        except Exception as e:
            print(f"Error getting file owner: {str(e)}")
            return None

    def get_optimal_gas_price(self):
        base_fee = self.w3_http.eth.get_block('latest').get('baseFeePerGas', 0)
        max_priority_fee = self.w3_http.eth.max_priority_fee
        if self.is_network_congested():
            return int((base_fee * 2) + max_priority_fee)  # Ensure return value is an integer
        return int(base_fee + max_priority_fee)  # Ensure return value is an integer

    def is_network_congested(self):
        latest_block = self.w3_http.eth.get_block('latest')
        gas_used_ratio = latest_block['gasUsed'] / latest_block['gasLimit']
        return gas_used_ratio > 0.8  # Consider network congested if gas usage is over 80%
