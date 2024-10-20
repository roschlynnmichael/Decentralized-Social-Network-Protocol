from eth_account import Account
import secrets

def generate_eth_address():
    priv = secrets.token_bytes(32)
    private_key = '0x' + priv.hex()
    account = Account.from_key(private_key)
    return account.address, private_key