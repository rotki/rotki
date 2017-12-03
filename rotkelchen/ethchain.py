import os
from urllib.request import Request, urlopen
from web3 import Web3, HTTPProvider
from requests import ConnectionError

from rotkelchen.utils import from_wei, rlk_jsonloads
from rotkelchen.fval import FVal


class Ethchain(object):
    def __init__(self):
        self.connected = True
        # Note that you should create only one RPCProvider per
        # process, as it recycles underlying TCP/IP network connections between
        # your process and Ethereum node
        self.web3 = Web3(HTTPProvider('http://localhost:8545'))
        try:
            self.web3.eth.blockNumber
            dir_path = os.path.dirname(os.path.realpath(__file__))
            with open(os.path.join(dir_path, 'data', 'token_abi.json'), 'r') as f:
                self.token_abi = rlk_jsonloads(f.read())
        except ConnectionError:
            print("INFO: Could not connect to a local ethereum node. Will use etherscan only")
            self.connected = False

    def get_eth_balance(self, account):
        # TODO
        pass

    def get_multieth_balance(self, accounts):
        eth_sum = FVal(0)
        if not self.connected:
            eth_resp = urlopen(Request(
                'https://api.etherscan.io/api?module=account&action=balancemulti&address=%s' %
                ','.join(accounts)
            ))
            eth_resp = rlk_jsonloads(eth_resp.read())
            if eth_resp['status'] != 1:
                import pdb
                pdb.set_trace()
                raise ValueError('Failed to query etherscan for accounts balance')
            eth_accounts = eth_resp['result']
            for account_entry in eth_accounts:
                eth_sum += FVal(account_entry['balance'])

        else:
            for account in accounts:
                eth_sum += FVal(self.web3.eth.getBalance(account))

        return from_wei(eth_sum)

    def get_multitoken_balance(self, token_symbol, token_address, token_decimals, accounts):
        token_amount = FVal(0)

        if self.connected:
            token_contract = self.web3.eth.contract(
                address=token_address,
                abi=self.token_abi
            )
            for account in accounts:
                token_amount += FVal(token_contract.call().balanceOf(account))
        else:
            for account in accounts:
                print('Checking token {} for account {}'.format(token_symbol, account))
                resp = urlopen(Request(
                    'https://api.etherscan.io/api?module=account&action='
                    'tokenbalance&contractaddress={}&address={}'.format(
                        token_address,
                        account,
                    )))
                resp = rlk_jsonloads(resp.read())
                if resp['status'] != 1:
                    raise ValueError(
                        'Failed to query etherscan for {} token balance of {}'.format(
                            token_symbol,
                            account,
                        ))
                token_amount += FVal(resp['result'])

        return token_amount / (FVal(10) ** FVal(token_decimals))
