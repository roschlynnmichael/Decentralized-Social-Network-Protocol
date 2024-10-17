import requests
from requests.auth import HTTPBasicAuth
import time
import json
from config import Config

class IPFSHandler:
    def __init__(self):
        self.ipfs_api_url = f'http://{Config.EC2_PUBLIC_IP}:8080/api/v0'
        self.auth = (Config.NGINX_USERNAME, Config.NGINX_PASSWORD)

    def add_content(self, content):
        try:
            files = {'file': ('filename', content)}
            headers = {
                'Host': Config.EC2_PUBLIC_IP,
                'X-Real-IP': '127.0.0.1',
                'X-Forwarded-For': '127.0.0.1',
                'X-Forwarded-Proto': 'http'
            }
            response = requests.post(f'{self.ipfs_api_url}/add', files=files, auth=self.auth, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.text)
                return result['Hash']
            else:
                raise Exception(f"Failed to add content to IPFS. Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"Error adding content to IPFS: {str(e)}")
            raise

    def get_content(self, ipfs_hash):
        try:
            response = requests.post(f'{self.ipfs_api_url}/cat?arg={ipfs_hash}', auth=self.auth)
            if response.status_code == 200:
                return response.content.decode('utf-8')
            else:
                raise Exception(f"Failed to get content from IPFS. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error getting content from IPFS: {str(e)}")
            raise

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
