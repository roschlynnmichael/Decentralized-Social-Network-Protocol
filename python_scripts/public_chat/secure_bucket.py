from cryptography.fernet import Fernet
import json
import time
from typing import Dict, List, Optional
from config import Config
from python_scripts.handlers.ipfs_handler import IPFSHandler
import hashlib

class SecureBucket:
    def __init__(self, node_id: str, username: str):
        self.node_id = node_id
        self.username = username
        self.bucket_id = f"user_{node_id}_bucket"
        self.ipfs_handler = IPFSHandler()
        
        # Initialize Fernet cipher with existing ENCRYPTION_KEY
        self.cipher_suite = Fernet(Config.ENCRYPTION_KEY)
        
        # Initialize bucket structure
        self.bucket_structure = {
            'metadata': {
                'owner_id': node_id,
                'owner_username': username,
                'created_at': time.time(),
                'last_updated': time.time()
            },
            'chat_history': [],
            'files': {}
        }
        
        # Initialize or load existing bucket
        self._init_bucket()

    def _init_bucket(self):
        """Initialize or load existing bucket"""
        try:
            # Try to get existing bucket hash from IPFS
            from app import bucket_manager  # Import here to avoid circular import
            bucket_hash = bucket_manager.get_bucket_hash(self.node_id)
            
            if bucket_hash:
                print(f"Loading existing bucket with hash: {bucket_hash}")
                # Get encrypted data from IPFS
                encrypted_data = self.ipfs_handler.get_content(bucket_hash)
                if encrypted_data:
                    # Decrypt and load bucket structure
                    self.bucket_structure = self._decrypt_data(encrypted_data)
                    print(f"Loaded bucket with {len(self.bucket_structure.get('files', {}))} files")
                else:
                    print("Failed to load bucket data from IPFS")
            else:
                print("Creating new bucket")
                # Create new bucket
                self._save_bucket()
        except Exception as e:
            print(f"Error initializing bucket: {e}")
            # Initialize empty bucket structure
            self.bucket_structure = {
                'metadata': {
                    'owner_id': self.node_id,
                    'owner_username': self.username,
                    'created_at': time.time(),
                    'last_updated': time.time()
                },
                'chat_history': [],
                'files': {}
            }

    def _encrypt_data(self, data: dict) -> bytes:
        """Encrypt data before storing in IPFS"""
        json_data = json.dumps(data)
        return self.cipher_suite.encrypt(json_data.encode())

    def _decrypt_data(self, encrypted_data: bytes) -> dict:
        """Decrypt data retrieved from IPFS"""
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        return json.loads(decrypted_data)

    def _save_bucket(self) -> str:
        """Save encrypted bucket to IPFS"""
        try:
            # Update last modified timestamp
            self.bucket_structure['metadata']['last_updated'] = time.time()
            
            # Encrypt and save
            encrypted_data = self._encrypt_data(self.bucket_structure)
            return self.ipfs_handler.add_content(encrypted_data)
        except Exception as e:
            print(f"Error saving bucket: {e}")
            raise

    def _load_bucket(self, bucket_hash: str):
        """Load and decrypt bucket from IPFS"""
        try:
            encrypted_data = self.ipfs_handler.get_content(bucket_hash)
            self.bucket_structure = self._decrypt_data(encrypted_data)
        except Exception as e:
            print(f"Error loading bucket: {e}")
            raise

    def _get_bucket_hash(self) -> Optional[str]:
        """Get latest bucket hash from IPFS"""
        try:
            # Get hash from bucket manager
            from app import bucket_manager  # Import here to avoid circular import
            return bucket_manager.get_bucket_hash(self.node_id)
        except Exception as e:
            print(f"Error getting bucket hash: {e}")
            return None

    def add_chat_message(self, message: Dict) -> str:
        """Add chat message to bucket"""
        try:
            # Create a copy of the message for storage
            storage_message = message.copy()
            
            # Encrypt only the content
            storage_message['content'] = self.cipher_suite.encrypt(
                message['content'].encode()
            ).decode()
            
            # Add message to chat history
            self.bucket_structure['chat_history'].append(storage_message)
            
            # Keep only last 100 messages
            if len(self.bucket_structure['chat_history']) > 100:
                self.bucket_structure['chat_history'] = self.bucket_structure['chat_history'][-100:]
            
            # Save updated bucket and return new hash
            return self._save_bucket()
        except Exception as e:
            print(f"Error adding chat message: {e}")
            raise

    def get_chat_history(self) -> List[Dict]:
        """Get decrypted chat history"""
        try:
            decrypted_history = []
            for message in self.bucket_structure['chat_history']:
                # Create a copy of the message
                decrypted_message = message.copy()
                # Decrypt only the content
                decrypted_message['content'] = self.cipher_suite.decrypt(
                    message['content'].encode()
                ).decode()
                decrypted_history.append(decrypted_message)
            return decrypted_history
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []

    def get_chat_history(self) -> List[Dict]:
        """Get decrypted chat history"""
        try:
            decrypted_history = []
            for message in self.bucket_structure['chat_history']:
                # Create a copy of the message
                decrypted_message = message.copy()
                # Decrypt only the content
                decrypted_message['content'] = self.cipher_suite.decrypt(
                    message['content'].encode()
                ).decode()
                decrypted_history.append(decrypted_message)
            return decrypted_history
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []

    def sync_chat_history(self, peer_bucket_hash: str):
        """Sync chat history with another peer's bucket"""
        try:
            # Get peer's bucket
            encrypted_data = self.ipfs_handler.get_content(peer_bucket_hash)
            peer_bucket = self._decrypt_data(encrypted_data)
            
            # Merge chat histories
            merged_history = self._merge_chat_histories(
                self.bucket_structure['chat_history'],
                peer_bucket['chat_history']
            )
            
            # Update local history
            self.bucket_structure['chat_history'] = merged_history
            
            # Save updated bucket
            return self._save_bucket()
            
        except Exception as e:
            print(f"Error syncing chat history: {e}")
            raise

    def _merge_chat_histories(self, history1: List[Dict], history2: List[Dict]) -> List[Dict]:
        """Merge two chat histories, removing duplicates"""
        # Combine histories and sort by timestamp
        all_messages = {msg['id']: msg for msg in history1 + history2}
        merged = list(all_messages.values())
        return sorted(merged, key=lambda x: x['timestamp'])

    def add_file(self, file_content: bytes, filename: str) -> dict:
        """Add a file to the bucket"""
        try:
            file_id = hashlib.sha256(f"{self.node_id}:{time.time()}".encode()).hexdigest()
            
            # Encrypt file content using Fernet cipher
            encrypted_content = self.cipher_suite.encrypt(file_content)
            
            # Add encrypted file to IPFS
            ipfs_hash = self.ipfs_handler.add_content(encrypted_content)
            print(f"Added file to IPFS with hash: {ipfs_hash}")
            
            # Add file metadata to bucket
            file_info = {
                'id': file_id,
                'name': filename,
                'ipfs_hash': ipfs_hash,
                'timestamp': time.time(),
                'size': len(file_content)
            }
            self.bucket_structure['files'][file_id] = file_info
            
            # Save updated bucket to IPFS
            new_bucket_hash = self._save_bucket()
            print(f"Updated bucket hash: {new_bucket_hash}")
            
            # Update bucket manager with new hash
            from app import bucket_manager
            bucket_manager.update_bucket_hash(self.node_id, new_bucket_hash)
            
            return file_info
        
        except Exception as e:
            print(f"Error adding file: {e}")
            raise

    def get_file_content(self, file_id: str) -> Optional[bytes]:
        """Get decrypted file content from bucket"""
        try:
            if file_id not in self.bucket_structure['files']:
                return None
            
            # Get file info from bucket
            file_info = self.bucket_structure['files'][file_id]
            
            # Get encrypted content from IPFS
            encrypted_content = self.ipfs_handler.get_content(file_info['ipfs_hash'])
            
            # Decrypt and return content
            return self.cipher_suite.decrypt(encrypted_content)
        
        except Exception as e:
            print(f"Error getting file content: {e}")
            raise

    def get_files(self) -> list:
        """Get list of files in bucket"""
        try:
            # Convert dictionary values to list and sort by timestamp
            files = list(self.bucket_structure.get('files', {}).values())
            print(f"Retrieved {len(files)} files from bucket structure")
            return sorted(files, key=lambda x: x['timestamp'], reverse=True)
        except Exception as e:
            print(f"Error getting files: {e}")
            return []

    def delete_file(self, file_id: str) -> bool:
        """Delete a file from the bucket"""
        try:
            if file_id in self.bucket_structure['files']:
                # Remove file from bucket structure
                del self.bucket_structure['files'][file_id]
                
                # Save updated bucket to IPFS
                self._save_bucket()
                return True
            
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def clear_chat_history(self):
        """Clear all chat history from bucket"""
        # Check if there are any messages to clear
        if not self.bucket_structure['chat_history']:
            return self._save_bucket()  # Return current hash if no messages to clear
        
        self.bucket_structure['chat_history'] = []
        return self._save_bucket()