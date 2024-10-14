import requests
from requests.auth import HTTPBasicAuth
import time

class IPFSHandler:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
        self.ipfs_api_url = "http://13.59.2.130:8080/api/v0"
        self.auth = HTTPBasicAuth('roschlynnmichael', 'Dsouza3191@')
        self.session = requests.Session()
        self.session.auth = self.auth
        self.connect_to_ipfs()

    def connect_to_ipfs(self):
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(f"{self.ipfs_api_url}/version")
                response.raise_for_status()
                print("Successfully connected to IPFS")
                return
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print("Failed to connect to IPFS after multiple attempts")
                    raise

    def add_file(self, file_path):
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = self.session.post(f"{self.ipfs_api_url}/add", files=files)
            response.raise_for_status()
            return response.json()['Hash']

    def get_file(self, file_hash):
        response = self.session.post(f"{self.ipfs_api_url}/cat", params={'arg': file_hash})
        response.raise_for_status()
        return response.content

    # Add more methods as needed for your IPFS operations
