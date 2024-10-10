import ipfshttpclient

class IPFSHandler:
    def __init__(self):
        try:
            # Connect to the IPFS daemon
            self.client = ipfshttpclient.connect('/dns/ipfs.io/tcp/443/https')
        except ipfshttpclient.exceptions.ConnectionError:
            print("Unable to connect to IPFS. Make sure the IPFS daemon is running.")
            self.client = None

    def add_file(self, file_path):
        """
        Add a file to IPFS and return its hash.
        """
        if not self.client:
            return None
        try:
            res = self.client.add(file_path)
            return res['Hash']
        except Exception as e:
            print(f"Error adding file to IPFS: {e}")
            return None

    def get_file(self, file_hash):
        """
        Retrieve a file from IPFS using its hash.
        """
        if not self.client:
            return None
        try:
            return self.client.cat(file_hash)
        except Exception as e:
            print(f"Error retrieving file from IPFS: {e}")
            return None

    def pin_file(self, file_hash):
        """
        Pin a file in IPFS to ensure it's not garbage collected.
        """
        if not self.client:
            return False
        try:
            self.client.pin.add(file_hash)
            return True
        except Exception as e:
            print(f"Error pinning file in IPFS: {e}")
            return False

    def add_json(self, json_data):
        """
        Add JSON data to IPFS and return its hash.
        """
        if not self.client:
            return None
        try:
            res = self.client.add_json(json_data)
            return res
        except Exception as e:
            print(f"Error adding JSON to IPFS: {e}")
            return None

    def get_json(self, json_hash):
        """
        Retrieve JSON data from IPFS using its hash.
        """
        if not self.client:
            return None
        try:
            return self.client.get_json(json_hash)
        except Exception as e:
            print(f"Error retrieving JSON from IPFS: {e}")
            return None

    def close(self):
        """
        Close the IPFS client connection.
        """
        if self.client:
            self.client.close()