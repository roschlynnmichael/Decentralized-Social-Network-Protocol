#0x939283adDA5c1fD7f14222DFD39Ce907a522D7ff

#faucets.chain.link

import web3
from web3.eth import get_balance
balance = get_balance('0x939283adDA5c1fD7f14222DFD39Ce907a522D7ff')
print(f"Balance: {web3.from_wei(balance, 'ether')} ETH")