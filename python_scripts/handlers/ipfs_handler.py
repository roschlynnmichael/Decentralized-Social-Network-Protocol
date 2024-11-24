import requests
import time
import json
from config import Config

class IPFSHandler:
    def __init__(self):
        self.ipfs_api_url = f'http://{Config.IPFS_API_HOST}:{Config.IPFS_API_PORT}/api/v0'
        self.timeout = Config.IPFS_TIMEOUT
        self.max_retries = 3

    def add_content(self, content):
        for attempt in range(self.max_retries):
            try:
                files = {'file': ('filename', content)}
                print(f"Attempt {attempt + 1}: Sending request to IPFS at {self.ipfs_api_url}")
                print(f"Content length: {len(content)}")
                
                response = requests.post(
                    f'{self.ipfs_api_url}/add',
                    files=files,
                    timeout=self.timeout,
                    headers={'Accept': 'application/json'}
                )
                
                print(f"IPFS response status: {response.status_code}")
                print(f"IPFS response content: {response.text[:200]}...")  # Print first 200 chars
                
                if response.status_code == 200:
                    result = json.loads(response.text)
                    return result['Hash']
                    
            except requests.Timeout:
                print(f"Attempt {attempt + 1} timed out after {self.timeout} seconds")
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)
        
        raise Exception(f"Failed to add content to IPFS after {self.max_retries} attempts")

    def get_content(self, ipfs_hash):
        try:
            response = requests.post(
                f'{self.ipfs_api_url}/cat?arg={ipfs_hash}',
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.content
            else:
                raise Exception(f"Failed to get content from IPFS. Status code: {response.status_code}")
        except requests.Timeout:
            print("IPFS request timed out")
            raise Exception("IPFS request timed out after {} seconds".format(self.timeout))
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
        return self.add_content(file_path)

    def get_file(self, file_hash):
        return self.get_content(file_hash)

    def check_ipfs_health(self):
        try:
            print(f"Checking IPFS health at {self.ipfs_api_url}")
            response = requests.get(
                f'{self.ipfs_api_url}/id',
                timeout=5
            )
            if response.status_code == 200:
                print("IPFS node is healthy")
                return True
            print(f"IPFS health check failed: Status code {response.status_code}")
            return False
        except Exception as e:
            print(f"IPFS health check failed: {str(e)}")
            return False

    # Add more methods as needed for your IPFS operations
