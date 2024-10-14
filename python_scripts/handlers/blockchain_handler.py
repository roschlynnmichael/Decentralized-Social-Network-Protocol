import json
import os
from web3 import Web3

class BlockchainHandler:
    def __init__(self, project_id):
        self.project_id = project_id
        self.w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{project_id}'))

        # Use an absolute path to the JSON file
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, 'json_files', 'UserRegistry.json')

        try:
            with open(json_path, 'r') as f:
                contract_abi = json.load(f)
            
            if not isinstance(contract_abi, list):
                raise ValueError("The JSON file should contain a list (the ABI)")
            
            self.contract_address = Web3.to_checksum_address('0xd9145CCE52D386f254917e481eB44e9943F39138')
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=contract_abi)
        except FileNotFoundError:
            print(f"Error: JSON file not found at {json_path}")
            raise
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in file at {json_path}")
            raise
        except ValueError as e:
            print(f"Error: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise

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
