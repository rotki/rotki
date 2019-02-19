import logging
import operator
from collections import defaultdict
from typing import Callable, Dict, List, Tuple, Union, cast

from eth_utils.address import to_checksum_address
from gevent.lock import Semaphore
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen import typing
from rotkehlchen.constants import (
    CACHE_RESPONSE_FOR_SECS,
    S_BTC,
    S_ETH,
    S_MLN,
    S_MLN_NEW,
    S_MLN_OLD,
)
from rotkehlchen.db.dbhandler import BlockchainAccounts
from rotkehlchen.errors import EthSyncError, InputError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils import (
    add_ints_or_combine_dicts,
    cache_response_timewise,
    request_get_direct,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Type Aliases used in this module
Balances = Dict[
    typing.BlockchainAsset,
    Dict[typing.BlockchainAddress, Dict[Union[str, typing.Asset], FVal]],
]
Totals = Dict[typing.BlockchainAsset, Dict[str, FVal]]
BlockchainBalancesUpdate = Dict[str, Union[Balances, Totals]]
EthBalances = Dict[typing.EthAddress, Dict[Union[typing.BlockchainAsset, str], FVal]]
AllEthTokens = Dict[typing.EthToken, Dict[str, Union[typing.ChecksumEthAddress, int]]]


class Blockchain(object):

    def __init__(
            self,
            blockchain_accounts: BlockchainAccounts,
            all_eth_tokens: List[typing.EthTokenInfo],
            owned_eth_tokens: List[typing.EthToken],
            inquirer: Inquirer,
            ethchain,  # TODO ethchain type not added yet due to Cyclic Dependency
    ):
        self.lock = Semaphore()
        self.results_cache: Dict[str, typing.ResultCache] = {}
        self.ethchain = ethchain
        self.inquirer = inquirer

        self.accounts = blockchain_accounts
        # go through ETH accounts and make sure they are EIP55 encoded
        # TODO: really really bad thing here. Should not have to force mutate
        # a named tuple. Move this into the named tuple constructor
        self.accounts._replace(eth=[to_checksum_address(x) for x in self.accounts.eth])

        self.owned_eth_tokens = owned_eth_tokens

        # All the known tokens, along with addresses and decimals
        self.all_eth_tokens: AllEthTokens = {}
        for token in all_eth_tokens:
            try:
                token_symbol = cast(typing.EthToken, str(token['symbol']))
            except (UnicodeDecodeError, UnicodeEncodeError):
                # skip tokens with problems in unicode encoding decoding
                continue

            self.all_eth_tokens[token_symbol] = {
                'address': to_checksum_address(token['address']),
                'decimal': cast(int, token['decimal']),
            }
        # Per account balances
        self.balances: Balances = defaultdict(dict)
        # Per asset total balances
        self.totals: Totals = defaultdict(dict)

    def __del__(self):
        del self.ethchain

    def set_eth_rpc_port(self, port: int) -> Tuple[bool, str]:
        return self.ethchain.set_rpc_port(port)

    @property
    def eth_tokens(self) -> List[typing.EthToken]:
        return self.owned_eth_tokens

    @cache_response_timewise(CACHE_RESPONSE_FOR_SECS)
    def query_balances(self) -> Tuple[Dict[str, Dict], str]:
        try:
            self.query_ethereum_balances()
        except BadFunctionCallOutput as e:
            log.error(
                'Assuming unsynced chain. Got web3 BadFunctionCallOutput '
                'exception: {}'.format(str(e)),
            )
            msg = (
                'Tried to use the ethereum chain of a local client to query '
                'an eth account but the chain is not synced.'
            )
            return {}, msg

        self.query_btc_balances()
        return {'per_account': self.balances, 'totals': self.totals}, ''

    @staticmethod
    def query_btc_account_balance(account: typing.BTCAddress) -> FVal:
        btc_resp = request_get_direct(
            'https://blockchain.info/q/addressbalance/%s' % account,
        )
        return FVal(btc_resp) * FVal('0.00000001')  # result is in satoshis

    def query_btc_balances(self) -> None:
        if len(self.accounts.btc) == 0:
            return

        self.balances[S_BTC] = {}
        btc_usd_price = self.inquirer.find_usd_price(S_BTC)
        total = FVal(0)
        for account in self.accounts.btc:
            balance = self.query_btc_account_balance(account)
            total += balance
            self.balances[S_BTC][account] = {
                'amount': balance,
                'usd_value': balance * btc_usd_price,
            }

        self.totals[S_BTC] = {'amount': total, 'usd_value': total * btc_usd_price}

    def query_token_balances(
            self,
            token_symbol: typing.EthToken,
            query_callback: Callable,
            **kwargs,
    ):
        """Query tokens by checking the eth_tokens mapping and using the respective query callback.

        The callback is either self.ethchain.get_multitoken_balance or
        self.ethchain.get_token_balance

        Some special logic is needed here since some token names may have special
        chararacters, for example for old/new migrated tokens."""
        if token_symbol == S_MLN:
            result1 = query_callback(
                token_symbol,
                self.all_eth_tokens[S_MLN_OLD]['address'],
                self.all_eth_tokens[S_MLN_OLD]['decimal'],
                **kwargs,
            )
            # TODO: Here is the place to start the warning event for the user if he
            # has any balance in the old MLN token:
            # https://github.com/rotkehlchenio/rotkehlchen/issues/277
            result2 = query_callback(
                token_symbol,
                self.all_eth_tokens[S_MLN_NEW]['address'],
                self.all_eth_tokens[S_MLN_NEW]['decimal'],
                **kwargs,
            )
            result = add_ints_or_combine_dicts(result1, result2)
        else:
            result = query_callback(
                token_symbol,
                self.all_eth_tokens[token_symbol]['address'],
                self.all_eth_tokens[token_symbol]['decimal'],
                **kwargs,
            )

        return result

    def track_new_tokens(self, tokens: List[typing.EthToken]) -> BlockchainBalancesUpdate:
        intersection = set(tokens).intersection(set(self.owned_eth_tokens))
        if intersection != set():
            raise InputError('Some of the new provided tokens to track already exist')

        self.owned_eth_tokens.extend(tokens)
        eth_balances = cast(EthBalances, self.balances[S_ETH])
        self.query_ethereum_tokens(tokens, eth_balances)
        return {'per_account': self.balances, 'totals': self.totals}

    def remove_eth_tokens(self, tokens: List[typing.EthToken]) -> BlockchainBalancesUpdate:
        for token in tokens:
            usd_price = self.inquirer.find_usd_price(token)
            for account, account_data in self.balances[S_ETH].items():
                if token not in account_data:
                    continue

                balance = account_data[token]
                deleting_usd_value = balance * usd_price
                del self.balances[S_ETH][account][token]
                self.balances[S_ETH][account]['usd_value'] = (
                    self.balances[S_ETH][account]['usd_value'] -
                    deleting_usd_value
                )

            del self.totals[token]
            self.owned_eth_tokens.remove(token)

        return {'per_account': self.balances, 'totals': self.totals}

    def modify_btc_account(
            self,
            account: typing.BTCAddress,
            append_or_remove: str,
            add_or_sub: Callable[[FVal, FVal], FVal],
    ) -> None:
        """Either appends or removes a BTC acccount.

        Call with 'append', operator.add to add the account
        Call with 'remove', operator.sub to remove the account
        """
        getattr(self.accounts.btc, append_or_remove)(account)
        btc_usd_price = self.inquirer.find_usd_price(S_BTC)
        balance = self.query_btc_account_balance(account)
        usd_balance = balance * btc_usd_price
        if append_or_remove == 'append':
            self.balances[S_BTC][account] = {'amount': balance, 'usd_value': usd_balance}
        elif append_or_remove == 'remove':
            del self.balances[S_BTC][account]
        else:
            raise ValueError('Programmer error: Should be append or remove')
        self.totals[S_BTC]['amount'] = add_or_sub(
            self.totals[S_BTC].get('amount', FVal(0)),
            balance,
        )
        self.totals[S_BTC]['usd_value'] = add_or_sub(
            self.totals[S_BTC].get('usd_value', FVal(0)),
            usd_balance,
        )

    def modify_eth_account(
            self,
            account: typing.EthAddress,
            append_or_remove: str,
            add_or_sub: Callable[[FVal, FVal], FVal],
    ) -> None:
        """Either appends or removes an ETH acccount.

        Call with 'append', operator.add to add the account
        Call with 'remove', operator.sub to remove the account
        """
        # Make sure account goes into web3.py as a properly checksummed address
        account = to_checksum_address(account)
        getattr(self.accounts.eth, append_or_remove)(account)
        eth_usd_price = self.inquirer.find_usd_price(S_ETH)
        balance = self.ethchain.get_eth_balance(account)
        usd_balance = balance * eth_usd_price
        if append_or_remove == 'append':
            self.balances[S_ETH][account] = {S_ETH: balance, 'usd_value': usd_balance}
        elif append_or_remove == 'remove':
            del self.balances[S_ETH][account]
        else:
            raise ValueError('Programmer error: Should be append or remove')
        self.totals[S_ETH]['amount'] = add_or_sub(
            self.totals[S_ETH].get('amount', FVal(0)),
            balance,
        )
        self.totals[S_ETH]['usd_value'] = add_or_sub(
            self.totals[S_ETH].get('usd_value', FVal(0)),
            usd_balance,
        )

        for token in self.owned_eth_tokens:
            usd_price = self.inquirer.find_usd_price(token)
            if usd_price == 0:
                # skip tokens that have no price
                continue

            token_balance = self.query_token_balances(
                token_symbol=token,
                query_callback=self.ethchain.get_token_balance,
                account=account,
            )
            if token_balance == 0:
                continue

            usd_value = token_balance * usd_price
            if append_or_remove == 'append':
                account_balance = self.balances[S_ETH][account]
                account_balance[token] = balance
                account_balance['usd_value'] = account_balance['usd_value'] + usd_value

            self.totals[token] = {
                'amount': add_or_sub(
                    self.totals[token].get('amount', FVal(0)),
                    token_balance,
                ),
                'usd_value': add_or_sub(
                    self.totals[token].get('usd_value', FVal(0)),
                    usd_value,
                ),
            }

    def add_blockchain_account(
            self,
            blockchain: str,
            account: typing.BlockchainAddress,
    ) -> BlockchainBalancesUpdate:
        return self.modify_blockchain_account(blockchain, account, 'append', operator.add)

    def remove_blockchain_account(
            self,
            blockchain: str,
            account: typing.BlockchainAddress,
    ) -> BlockchainBalancesUpdate:
        return self.modify_blockchain_account(blockchain, account, 'remove', operator.sub)

    def modify_blockchain_account(
            self,
            blockchain: str,
            account: typing.BlockchainAddress,
            append_or_remove: str,
            add_or_sub: Callable[[FVal, FVal], FVal],
    ) -> BlockchainBalancesUpdate:

        if blockchain == S_BTC:
            if append_or_remove == 'remove' and account not in self.accounts.btc:
                raise InputError('Tried to remove a non existing BTC account')

            # above we check that account is a BTC account
            self.modify_btc_account(
                typing.BTCAddress(account),
                append_or_remove,
                add_or_sub,
            )

        elif blockchain == S_ETH:
            if append_or_remove == 'remove' and account not in self.accounts.eth:
                raise InputError('Tried to remove a non existing ETH account')
            try:
                # above we check that account is an ETH account
                self.modify_eth_account(typing.EthAddress(account), append_or_remove, add_or_sub)
            except BadFunctionCallOutput as e:
                log.error(
                    'Assuming unsynced chain. Got web3 BadFunctionCallOutput '
                    'exception: {}'.format(str(e)),
                )
                raise EthSyncError(
                    'Tried to use the ethereum chain of a local client to edit '
                    'an eth account but the chain is not synced.',
                )

        else:
            raise InputError(
                'Unsupported blockchain {} provided at remove_blockchain_account'.format(
                    blockchain),
            )

        return {'per_account': self.balances, 'totals': self.totals}

    def query_ethereum_tokens(
            self,
            tokens: List[typing.EthToken],
            eth_balances: EthBalances,
    ) -> None:
        token_balances = {}
        token_usd_price = {}
        for token in tokens:
            usd_price = self.inquirer.find_usd_price(token)
            if usd_price == 0:
                # skip tokens that have no price
                continue
            token_usd_price[token] = usd_price

            token_balances[token] = self.query_token_balances(
                token_symbol=token,
                query_callback=self.ethchain.get_multitoken_balance,
                accounts=self.accounts.eth,
            )

        for token, token_accounts in token_balances.items():
            token_total = FVal(0)
            for account, balance in token_accounts.items():
                token_total += balance
                usd_value = balance * token_usd_price[token]
                eth_balances[account][token] = balance
                eth_balances[account]['usd_value'] = eth_balances[account]['usd_value'] + usd_value

            self.totals[token] = {
                'amount': token_total,
                'usd_value': token_total * token_usd_price[token],
            }

        self.balances[S_ETH] = cast(
            Dict[typing.BlockchainAddress, Dict[Union[str, typing.Asset], FVal]],
            eth_balances,
        )

    def query_ethereum_balances(self) -> None:
        if len(self.accounts.eth) == 0:
            return

        eth_accounts = self.accounts.eth
        eth_usd_price = self.inquirer.find_usd_price(S_ETH)
        balances = self.ethchain.get_multieth_balance(eth_accounts)
        eth_total = FVal(0)
        eth_balances = {}
        for account, balance in balances.items():
            eth_total += balance
            eth_balances[account] = {S_ETH: balance, 'usd_value': balance * eth_usd_price}

        self.totals[S_ETH] = {'amount': eth_total, 'usd_value': eth_total * eth_usd_price}
        self.balances[S_ETH] = eth_balances  # but they are not complete until token query

        # And now for tokens
        self.query_ethereum_tokens(self.owned_eth_tokens, eth_balances)
