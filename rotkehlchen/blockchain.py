import logging
import operator
from collections import defaultdict
from typing import Callable, Dict, List, Tuple, Union, cast

from eth_utils.address import to_checksum_address
from gevent.lock import Semaphore
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.assets import Asset
from rotkehlchen.assets.converters import asset_from_eth_token_symbol
from rotkehlchen.constants import A_BTC, A_ETH, CACHE_RESPONSE_FOR_SECS
from rotkehlchen.db.dbhandler import BlockchainAccounts
from rotkehlchen.errors import EthSyncError, InputError, UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import (
    BlockchainAddress,
    BTCAddress,
    ChecksumEthAddress,
    EthAddress,
    EthToken,
    EthTokenInfo,
    ResultCache,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils import cache_response_timewise, request_get_direct

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Type Aliases used in this module
Balances = Dict[
    Asset,
    Dict[BlockchainAddress, Dict[Union[str, Asset], FVal]],
]
Totals = Dict[Asset, Dict[str, FVal]]
BlockchainBalancesUpdate = Dict[str, Union[Balances, Totals]]
EthBalances = Dict[EthAddress, Dict[Union[Asset, str], FVal]]
AllEthTokens = Dict[Asset, Dict[str, Union[ChecksumEthAddress, int]]]


class Blockchain(object):

    def __init__(
            self,
            blockchain_accounts: BlockchainAccounts,
            all_eth_tokens: List[EthTokenInfo],
            owned_eth_tokens: List[EthToken],
            inquirer: Inquirer,
            ethchain,  # TODO ethchain type not added yet due to Cyclic Dependency
            msg_aggregator: MessagesAggregator,
    ):
        self.lock = Semaphore()
        self.results_cache: Dict[str, ResultCache] = {}
        self.ethchain = ethchain
        self.inquirer = inquirer
        self.msg_aggregator = msg_aggregator

        self.accounts = blockchain_accounts
        # go through ETH accounts and make sure they are EIP55 encoded
        # TODO: really really bad thing here. Should not have to force mutate
        # a named tuple. Move this into the named tuple constructor
        self.accounts._replace(eth=[to_checksum_address(x) for x in self.accounts.eth])

        # The tokens we own
        self.owned_eth_tokens: List[Asset] = []
        for token_symbol in owned_eth_tokens:
            try:
                self.owned_eth_tokens.append(asset_from_eth_token_symbol(token_symbol))
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found owned eth token with symbol '
                    f'{e.asset_name} that is not supported. Ignoring it.',
                )
                continue

        # All the known tokens, along with addresses and decimals
        self.all_eth_tokens: AllEthTokens = {}
        for token_info in all_eth_tokens:
            try:
                token_asset = asset_from_eth_token_symbol(token_info.symbol)
            except UnsupportedAsset as e:
                log.warning(
                    f'Ignoring eth token {e.asset_name} from the known '
                    f'tokens list as it is not supported',
                )
                continue

            self.all_eth_tokens[token_asset] = {
                'address': to_checksum_address(token_info.address),
                'decimal': token_info.decimal,
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
    def eth_tokens(self) -> List[Asset]:
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
    def query_btc_account_balance(account: BTCAddress) -> FVal:
        btc_resp = request_get_direct(
            'https://blockchain.info/q/addressbalance/%s' % account,
        )
        return FVal(btc_resp) * FVal('0.00000001')  # result is in satoshis

    def query_btc_balances(self) -> None:
        if len(self.accounts.btc) == 0:
            return

        self.balances[A_BTC] = {}
        btc_usd_price = self.inquirer.find_usd_price(A_BTC)
        total = FVal(0)
        for account in self.accounts.btc:
            balance = self.query_btc_account_balance(account)
            total += balance
            self.balances[A_BTC][account] = {
                'amount': balance,
                'usd_value': balance * btc_usd_price,
            }

        self.totals[A_BTC] = {'amount': total, 'usd_value': total * btc_usd_price}

    def query_token_balances(
            self,
            token_asset: Asset,
            query_callback: Callable,
            **kwargs,
    ):
        """Query tokens by checking the eth_tokens mapping and using the respective query callback.

        The callback is either self.ethchain.get_multitoken_balance or
        self.ethchain.get_token_balance

        Some special logic is needed here since some token names may have special
        chararacters, for example for old/new migrated tokens."""

        # TODO: Since all_eth_tokens now contains Assets as keys, checking up old
        # symbols for querying balances for old tokens to warn the user or convert
        # to new balance does not work from here anymore. Find a way to do it again
        # with the new functionality

        # if token_symbol == S_MLN:
        #     result1 = query_callback(
        #         token_symbol,
        #         self.all_eth_tokens[S_MLN_OLD]['address'],
        #         self.all_eth_tokens[S_MLN_OLD]['decimal'],
        #         **kwargs,
        #     )
        #     # TODO: Here is the place to start the warning event for the user if he
        #     # has any balance in the old MLN token:
        #     # https://github.com/rotkehlchenio/rotkehlchen/issues/277
        #     result2 = query_callback(
        #         token_symbol,
        #         self.all_eth_tokens[S_MLN_NEW]['address'],
        #         self.all_eth_tokens[S_MLN_NEW]['decimal'],
        #         **kwargs,
        #     )
        #     result = add_ints_or_combine_dicts(result1, result2)
        # else:
        result = query_callback(
            token_asset,
            self.all_eth_tokens[token_asset]['address'],
            self.all_eth_tokens[token_asset]['decimal'],
            **kwargs,
        )

        return result

    def track_new_tokens(self, tokens: List[EthToken]) -> BlockchainBalancesUpdate:

        new_tokens = []
        for token_symbol in tokens:
            try:
                new_tokens.append(asset_from_eth_token_symbol(token_symbol))
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Tried to add unsupported eth token with symbol '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue

        intersection = set(new_tokens).intersection(set(self.owned_eth_tokens))
        if intersection != set():
            raise InputError('Some of the new provided tokens to track already exist')

        self.owned_eth_tokens.extend(new_tokens)
        eth_balances = cast(EthBalances, self.balances[A_ETH])
        self.query_ethereum_tokens(new_tokens, eth_balances)
        return {'per_account': self.balances, 'totals': self.totals}

    def remove_eth_tokens(self, tokens: List[EthToken]) -> BlockchainBalancesUpdate:
        for token_symbol in tokens:
            try:
                token = asset_from_eth_token_symbol(token_symbol)
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Tried to remove unsupported eth token with symbol '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue

            usd_price = self.inquirer.find_usd_price(token)
            for account, account_data in self.balances[A_ETH].items():
                if token not in account_data:
                    continue

                balance = account_data[token]
                deleting_usd_value = balance * usd_price
                del self.balances[A_ETH][account][token]
                self.balances[A_ETH][account]['usd_value'] = (
                    self.balances[A_ETH][account]['usd_value'] -
                    deleting_usd_value
                )

            del self.totals[token]
            self.owned_eth_tokens.remove(token)

        return {'per_account': self.balances, 'totals': self.totals}

    def modify_btc_account(
            self,
            account: BTCAddress,
            append_or_remove: str,
            add_or_sub: Callable[[FVal, FVal], FVal],
    ) -> None:
        """Either appends or removes a BTC acccount.

        Call with 'append', operator.add to add the account
        Call with 'remove', operator.sub to remove the account
        """
        getattr(self.accounts.btc, append_or_remove)(account)
        btc_usd_price = self.inquirer.find_usd_price(A_BTC)
        balance = self.query_btc_account_balance(account)
        usd_balance = balance * btc_usd_price
        if append_or_remove == 'append':
            self.balances[A_BTC][account] = {'amount': balance, 'usd_value': usd_balance}
        elif append_or_remove == 'remove':
            del self.balances[A_BTC][account]
        else:
            raise ValueError('Programmer error: Should be append or remove')
        self.totals[A_BTC]['amount'] = add_or_sub(
            self.totals[A_BTC].get('amount', FVal(0)),
            balance,
        )
        self.totals[A_BTC]['usd_value'] = add_or_sub(
            self.totals[A_BTC].get('usd_value', FVal(0)),
            usd_balance,
        )

    def modify_eth_account(
            self,
            account: EthAddress,
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
        eth_usd_price = self.inquirer.find_usd_price(A_ETH)
        balance = self.ethchain.get_eth_balance(account)
        usd_balance = balance * eth_usd_price
        if append_or_remove == 'append':
            self.balances[A_ETH][account] = {A_ETH: balance, 'usd_value': usd_balance}
        elif append_or_remove == 'remove':
            del self.balances[A_ETH][account]
        else:
            raise ValueError('Programmer error: Should be append or remove')
        self.totals[A_ETH]['amount'] = add_or_sub(
            self.totals[A_ETH].get('amount', FVal(0)),
            balance,
        )
        self.totals[A_ETH]['usd_value'] = add_or_sub(
            self.totals[A_ETH].get('usd_value', FVal(0)),
            usd_balance,
        )

        for token in self.owned_eth_tokens:
            usd_price = self.inquirer.find_usd_price(token)
            if usd_price == 0:
                # skip tokens that have no price
                continue

            token_balance = self.query_token_balances(
                token_asset=token,
                query_callback=self.ethchain.get_token_balance,
                account=account,
            )
            if token_balance == 0:
                continue

            usd_value = token_balance * usd_price
            if append_or_remove == 'append':
                account_balance = self.balances[A_ETH][account]
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
            account: BlockchainAddress,
    ) -> BlockchainBalancesUpdate:
        return self.modify_blockchain_account(blockchain, account, 'append', operator.add)

    def remove_blockchain_account(
            self,
            blockchain: str,
            account: BlockchainAddress,
    ) -> BlockchainBalancesUpdate:
        return self.modify_blockchain_account(blockchain, account, 'remove', operator.sub)

    def modify_blockchain_account(
            self,
            blockchain: str,
            account: BlockchainAddress,
            append_or_remove: str,
            add_or_sub: Callable[[FVal, FVal], FVal],
    ) -> BlockchainBalancesUpdate:

        if blockchain == A_BTC:
            if append_or_remove == 'remove' and account not in self.accounts.btc:
                raise InputError('Tried to remove a non existing BTC account')

            # above we check that account is a BTC account
            self.modify_btc_account(
                BTCAddress(account),
                append_or_remove,
                add_or_sub,
            )

        elif blockchain == A_ETH:
            if append_or_remove == 'remove' and account not in self.accounts.eth:
                raise InputError('Tried to remove a non existing ETH account')
            try:
                # above we check that account is an ETH account
                self.modify_eth_account(EthAddress(account), append_or_remove, add_or_sub)
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
            tokens: List[Asset],
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
                token_asset=token,
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

        self.balances[A_ETH] = cast(
            Dict[BlockchainAddress, Dict[Union[str, Asset], FVal]],
            eth_balances,
        )

    def query_ethereum_balances(self) -> None:
        if len(self.accounts.eth) == 0:
            return

        eth_accounts = self.accounts.eth
        eth_usd_price = self.inquirer.find_usd_price(A_ETH)
        balances = self.ethchain.get_multieth_balance(eth_accounts)
        eth_total = FVal(0)
        eth_balances: EthBalances = {}
        for account, balance in balances.items():
            eth_total += balance
            eth_balances[account] = {A_ETH: balance, 'usd_value': balance * eth_usd_price}

        self.totals[A_ETH] = {'amount': eth_total, 'usd_value': eth_total * eth_usd_price}
        # but they are not complete until token query
        self.balances[A_ETH] = cast(
            Dict[BlockchainAddress, Dict[Union[str, Asset], FVal]],
            eth_balances,
        )

        # And now for tokens
        self.query_ethereum_tokens(self.owned_eth_tokens, eth_balances)
