import os
from web3 import Web3
import requests
import ipfshttpclient

class InfuraHandler:
    def __init__(self, project_id=None):
        self.project_id = project_id or os.getenv('INFURA_PROJECT_ID')
        if not self.project_id:
            raise ValueError("Infura Project ID must be provided or set as INFURA_PROJECT_ID environment variable")
        self.ethereum = self.EthereumHandler(self.project_id)
        self.ipfs = self.IPFSHandler()

    class EthereumHandler:
        def __init__(self, project_id):
            self.https_w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{project_id}'))
            self.ws_w3 = Web3(Web3.WebSocketProvider(f'wss://mainnet.infura.io/ws/v3/{project_id}'))
        def check_https_connection(self):
            return self.https_w3.is_connected()
        def check_ws_connection(self):
            return self.ws_w3.is_connected()
        def get_latest_block(self):
            return self.https_w3.eth.get_block('latest')
        def get_balance(self, address):
            return self.https_w3.eth.get_balance(address)
        def get_gas_price(self):
            return self.https_w3.eth.gas_price
        def estimate_transaction_cost(self, from_address, to_address, value):
            gas_estimate = self.https_w3.eth.estimate_gas(
                from_address=from_address,
                to_address=to_address,
                value=value
            )
            gas_price = self.get_gas_price()
            return gas_estimate * gas_price
        def send_transaction(self, transaction):
            return self.https_w3.eth.send_raw_transaction(transaction)
        def listen_for_new_blocks(self, callback):
            def handle_event(event):
                callback(self.ws_w3.eth.get_block(event))
            new_block_filter = self.ws_w3.eth.filter('latest')
            new_block_filter.watch(handle_event)
    
    class IPFSHandler:
        def __init__(self):
            self.client = ipfshttpclient.connect('/dns/ipfs.io/tcp/443/https')
        def add_file(self, file_path):
            res = self.client.add(file_path)
            return res['Hash']
        def get_file(self, file_hash):
            return self.client.cat(file_hash)
        def pin_file(self, file_hash):
            return self.client.pin.add(file_hash)
            
            
        