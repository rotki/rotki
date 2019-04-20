import logging
import os
from typing import Dict, List, Optional, Tuple

import requests
from web3 import HTTPProvider, Web3

from rotkehlchen import typing
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import from_wei, request_get_dict
from rotkehlchen.utils.serialization import rlk_jsonloads

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Ethchain(object):
    def __init__(self, ethrpc_port: int, attempt_connect: bool = True):
        self.web3: Web3 = None
        self.rpc_port = ethrpc_port
        self.connected = False
        if attempt_connect:
            self.attempt_connect(ethrpc_port)

    def __del__(self):
        if self.web3:
            del self.web3

    def attempt_connect(self, ethrpc_port: int, mainnet_check=True) -> Tuple[bool, str]:
        if self.rpc_port == ethrpc_port and self.connected:
            # We are already connected
            return True, 'Already connected to an ethereum node'

        if self.web3:
            del self.web3

        try:
            self.web3 = Web3(HTTPProvider('http://localhost:{}'.format(ethrpc_port)))
        except requests.exceptions.ConnectionError:
            log.warning('Could not connect to a local ethereum node. Will use etherscan only')
            self.connected = False
            return False, 'Failed to connect to ethereum node at port {}'.format(ethrpc_port)

        if self.web3.isConnected():
            dir_path = os.path.dirname(os.path.realpath(__file__))
            with open(os.path.join(dir_path, 'data', 'token_abi.json'), 'r') as f:
                self.token_abi = rlk_jsonloads(f.read())

            # Also make sure we are actually connected to the Ethereum mainnet
            if mainnet_check:
                genesis_hash = self.web3.eth.getBlock(0)['hash'].hex()  # pylint: disable=no-member
                target = '0xd4e56740f876aef8c010b86a40d5f56745a118d0906a34e69aec8c0db1cb8fa3'
                if genesis_hash != target:
                    log.warning(
                        'Connected to a local ethereum node but it is not on the ethereum mainnet',
                    )
                    self.connected = False
                    message = (
                        'Connected to ethereum node at port {} but it is not on '
                        'the ethereum mainnet'.format(ethrpc_port)
                    )
                    return False, message
                if self.web3.eth.syncing:  # pylint: disable=no-member
                    current_block = self.web3.eth.syncing.currentBlock  # pylint: disable=no-member
                    latest_block = self.web3.eth.syncing.highestBlock  # pylint: disable=no-member
                    return self.is_synchronized(current_block, latest_block)
                else:
                    current_block = self.web3.eth.blockNumber  # pylint: disable=no-member
                    latest_block = self.query_eth_highest_block()
                    if latest_block is None:
                        return False, 'Could not query latest block from blockcypher.'
                    return self.is_synchronized(current_block, latest_block)

            self.connected = True
            return True, ''
        else:
            log.warning('Could not connect to a local ethereum node. Will use etherscan only')
            self.connected = False
            message = 'Failed to connect to ethereum node at port {}'.format(ethrpc_port)

        # If we get here we did not connnect
        return False, message

    def is_synchronized(self, current_block: int, latest_block: int) -> Tuple[bool, str]:
        """ Validate that the local ethereum node is synchronized
            within 20 blocks of latest block

        Returns a tuple (results, message)
            - result: Boolean for confirmation of synchronized
            - message: A message containing information on what the status is. """
        if current_block < (latest_block - 20):
            message = (
                'Found local ethereum node but it is out of sync. Will use etherscan.'
            )
            log.warning(message)
            self.connected = False
            return False, message

        return True, message

    def set_rpc_port(self, port: int) -> Tuple[bool, str]:
        """ Attempts to set the RPC port for the ethereum client.

        Returns a tuple (result, message)
            - result: Boolean for success or failure of changing the rpc port
            - message: A message containing information on what happened. Can
                       be populated both in case of success or failure"""
        result, message = self.attempt_connect(port)
        if result:
            log.info('Setting ETH RPC port', port=port)
            self.ethrpc_port = port
        return result, message

    @staticmethod
    def query_eth_highest_block() -> Optional[int]:
        """ Attempts to query blockcypher for the block height

        Returns the highest blockNumber"""

        url = 'https://api.blockcypher.com/v1/eth/main'
        log.debug('Querying ETH highest block', url=url)
        eth_resp = request_get_dict(url)

        if 'height' not in eth_resp:
            return None
        block_number = int(eth_resp['height'])
        log.debug('ETH highest block result', block=block_number)
        return block_number

    def get_eth_balance(self, account: typing.EthAddress) -> FVal:
        if not self.connected:
            log.debug(
                'Querying etherscan for account balance',
                sensitive_log=True,
                eth_address=account,
            )
            eth_resp = request_get_dict(
                'https://api.etherscan.io/api?module=account&action=balance&address=%s'
                % account,
            )
            if eth_resp['status'] != 1:
                raise ValueError('Failed to query etherscan for accounts balance')
            amount = FVal(eth_resp['result'])

            log.debug(
                'Etherscan account balance result',
                sensitive_log=True,
                eth_address=account,
                wei_amount=amount,
            )
            return from_wei(amount)
        else:
            wei_amount = self.web3.eth.getBalance(account)  # pylint: disable=no-member
            log.debug(
                'Ethereum node account balance result',
                sensitive_log=True,
                eth_address=account,
                wei_amount=wei_amount,
            )
            return from_wei(wei_amount)

    def get_multieth_balance(
            self,
            accounts: List[typing.EthAddress],
    ) -> Dict[typing.EthAddress, FVal]:
        """Returns a dict with keys being accounts and balances in ETH"""
        balances = {}

        if not self.connected:
            if len(accounts) > 20:
                new_accounts = [accounts[x:x + 2] for x in range(0, len(accounts), 2)]
            else:
                new_accounts = [accounts]

            for account_slice in new_accounts:
                log.debug(
                    'Querying etherscan for multiple accounts balance',
                    sensitive_log=True,
                    eth_accounts=account_slice,
                )
                eth_resp = request_get_dict(
                    'https://api.etherscan.io/api?module=account&action=balancemulti&address=%s' %
                    ','.join(account_slice),
                )
                if eth_resp['status'] != 1:
                    raise ValueError('Failed to query etherscan for accounts balance')
                eth_accounts = eth_resp['result']

                for account_entry in eth_accounts:
                    amount = FVal(account_entry['balance'])
                    balances[account_entry['account']] = from_wei(amount)
                    log.debug(
                        'Etherscan account balance result',
                        sensitive_log=True,
                        eth_address=account_entry['account'],
                        wei_amount=amount,
                    )

        else:
            for account in accounts:
                amount = FVal(self.web3.eth.getBalance(account))  # pylint: disable=no-member
                log.debug(
                    'Ethereum node balance result',
                    sensitive_log=True,
                    eth_address=account,
                    wei_amount=amount,
                )
                balances[account] = from_wei(amount)

        return balances

    def get_multitoken_balance(
            self,
            token: EthereumToken,
            accounts: List[typing.EthAddress],
    ) -> Dict[typing.EthAddress, FVal]:
        """Return a dictionary with keys being accounts and value balances of token
        Balance value is normalized through the token decimals.
        """
        balances = {}
        if self.connected:
            token_contract = self.web3.eth.contract(  # pylint: disable=no-member
                address=token.ethereum_address,
                abi=self.token_abi,
            )

            for account in accounts:
                log.debug(
                    'Ethereum node query for token balance',
                    sensitive_log=True,
                    eth_address=account,
                    token_address=token.ethereum_address,
                    token_symbol=token.decimals,
                )
                token_amount = FVal(token_contract.functions.balanceOf(account).call())
                if token_amount != 0:
                    balances[account] = token_amount / (FVal(10) ** FVal(token.decimals))
                log.debug(
                    'Ethereum node result for token balance',
                    sensitive_log=True,
                    eth_address=account,
                    token_address=token.ethereum_address,
                    token_symbol=token.symbol,
                    amount=token_amount,
                )
        else:
            for account in accounts:
                log.debug(
                    'Querying Etherscan for token balance',
                    sensitive_log=True,
                    eth_address=account,
                    token_address=token.ethereum_address,
                    token_symbol=token.symbol,
                )
                resp = request_get_dict(
                    'https://api.etherscan.io/api?module=account&action='
                    'tokenbalance&contractaddress={}&address={}'.format(
                        token.ethereum_address,
                        account,
                    ))
                if resp['status'] != 1:
                    raise ValueError(
                        'Failed to query etherscan for {} token balance of {}'.format(
                            token.symbol,
                            account,
                        ))
                token_amount = FVal(resp['result'])
                if token_amount != 0:
                    balances[account] = token_amount / (FVal(10) ** FVal(token.decimals))
                log.debug(
                    'Etherscan result for token balance',
                    sensitive_log=True,
                    eth_address=account,
                    token_address=token.ethereum_address,
                    token_symbol=token.symbol,
                    amount=token_amount,
                )

        return balances

    def get_token_balance(
            self,
            token: EthereumToken,
            account: typing.EthAddress,
    ) -> FVal:
        res = self.get_multitoken_balance(token=token, accounts=[account])
        return res.get(account, FVal(0))

    def get_block_by_number(self, num: int):
        if not self.connected:
            return None

        return self.web3.eth.getBlock(num)  # pylint: disable=no-member
