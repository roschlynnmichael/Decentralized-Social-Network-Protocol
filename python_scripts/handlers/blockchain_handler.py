import json
import os
from web3 import Web3

class BlockchainHandler:
    def __init__(self, project_id=None):
        # For local development, we don't need a real provider
        self.w3 = Web3(Web3.EthereumTesterProvider())

        # Load the contract JSON file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, '..', '..', 'json_files', 'useregistry.json')
        
        with open(json_path, 'r') as f:
            contract_json = json.load(f)

        self.contract_abi = contract_json['abi']
        self.contract_address = Web3.to_checksum_address(contract_json['networks']['1337']['address'])

        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)

    def check_https_connection(self):
        return self.http_w3.is_connected()
    
    def check_ws_connection(self):
        return self.ws_w3.is_connected()
    
    def get_latest_block(self):
        return self.http_w3.eth.get_block('latest')
    
    def get_balance(self, address):
        return self.http_w3.eth.get_balance(address)
    
    def get_gas_price(self):
        return self.http_w3.eth.gas_price
    
    def estimate_transaction_cost(self, from_address, to_address, value):
        gas_estimate = self.http_w3.eth.estimate_gas(
            from_address = from_address,
            to_address = to_address,
            value = value
        )
        gas_price = self.get_gas_price()
        return gas_estimate * gas_price
    
    def send_transaction(self, transaction):
        return self.http_w3.eth.send_raw_transaction(transaction)
    
    def listen_to_new_blocks(self, callback):
        def handle_event(event):
            callback(self.ws_w3.eth.get_block(event))
        new_block_filter = self.ws_w3.eth.filter('latest')
        new_block_filter.watch(handle_event)

    def store_user_interaction(self, user1, user2, interaction_type):
        pass

    def verify_content_ownership(self, user, content_hash):
        pass
    
    def create_user(self, username, eth_address):
        # Ensure the address is checksum
        eth_address = Web3.to_checksum_address(eth_address)

        # Get the function to call
        func = self.contract.functions.registerUser(username, eth_address)

        # Estimate gas
        gas_estimate = func.estimate_gas()

        # Get the current gas price
        gas_price = self.http_w3.eth.gas_price

        # Build the transaction
        transaction = func.build_transaction({
            'from': eth_address,
            'gas': gas_estimate,
            'gasPrice': gas_price,
            'nonce': self.http_w3.eth.get_transaction_count(eth_address),
        })

        return transaction

    def get_user(self, eth_address):
        eth_address = Web3.to_checksum_address(eth_address)
        return self.contract.functions.getUser(eth_address).call()

    def user_exists(self, eth_address):
        eth_address = Web3.to_checksum_address(eth_address)
        return self.contract.functions.userExists(eth_address).call()

    def register_user(self, username, eth_address):
        return self.contract.functions.registerUser(username, eth_address).build_transaction({
            'from': eth_address,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(eth_address),
        })
