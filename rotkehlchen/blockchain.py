import logging
import operator
from collections import defaultdict
from copy import deepcopy
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple, Union, cast, overload

from eth_utils.address import to_checksum_address
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.errors import EthSyncError, InputError, InvalidBTCAddress
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import (
    BlockchainAddress,
    BTCAddress,
    ChecksumEthAddress,
    EthAddress,
    SupportedBlockchain,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import (
    CacheableObject,
    cache_response_timewise,
    request_get_direct,
    satoshis_to_btc,
)

if TYPE_CHECKING:
    from rotkehlchen.ethchain import Ethchain

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Type Aliases used in this module
Balances = Dict[
    Asset,
    Dict[BlockchainAddress, Dict[Union[str, Asset], FVal]],
]
Totals = Dict[Asset, Dict[str, FVal]]
BlockchainBalancesUpdate = Dict[str, Union[Balances, Totals]]
EthBalances = Dict[ChecksumEthAddress, Dict[Union[Asset, str], FVal]]


class Blockchain(CacheableObject):

    def __init__(
            self,
            blockchain_accounts: BlockchainAccounts,
            owned_eth_tokens: List[EthereumToken],
            ethchain: 'Ethchain',
            msg_aggregator: MessagesAggregator,
    ):
        self.ethchain = ethchain
        self.msg_aggregator = msg_aggregator
        self.owned_eth_tokens = owned_eth_tokens

        self.accounts = blockchain_accounts
        # go through ETH accounts and make sure they are EIP55 encoded
        # TODO: really really bad thing here. Should not have to force mutate
        # a named tuple. Move this into the named tuple constructor
        self.accounts._replace(eth=[to_checksum_address(x) for x in self.accounts.eth])

        # Per account balances
        self.balances: Balances = defaultdict(dict)
        # Per asset total balances
        self.totals: Totals = defaultdict(dict)

        super().__init__()

    def __del__(self) -> None:
        del self.ethchain

    def set_eth_rpc_endpoint(self, endpoint: str) -> Tuple[bool, str]:
        return self.ethchain.set_rpc_endpoint(endpoint)

    @property
    def eth_tokens(self) -> List[EthereumToken]:
        return self.owned_eth_tokens

    @cache_response_timewise()
    def query_balances(
            self,
            blockchain: Optional[SupportedBlockchain],
    ) -> Tuple[Optional[Dict[str, Dict]], str]:
        should_query_eth = not blockchain or blockchain == SupportedBlockchain.ETHEREUM
        should_query_btc = not blockchain or blockchain == SupportedBlockchain.BITCOIN

        if should_query_eth:
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
                return None, msg

        if not blockchain or blockchain == SupportedBlockchain.BITCOIN:
            self.query_btc_balances()

        per_account = deepcopy(self.balances)
        totals = deepcopy(self.totals)
        if not should_query_eth:
            per_account.pop(A_ETH, None)
            # only keep BTC, remove ETH and any tokens that may be in the result
            totals = {A_BTC: totals[A_BTC]}
        if not should_query_btc:
            per_account.pop(A_BTC, None)
            totals.pop(A_BTC, None)

        return {'per_account': per_account, 'totals': totals}, ''

    @staticmethod
    def query_btc_account_balance(account: BTCAddress) -> FVal:
        try:
            btc_resp = request_get_direct(
                url='https://blockchain.info/q/addressbalance/%s' % account,
                handle_429=True,
                # If we get a 429 then their docs suggest 10 seconds
                # https://blockchain.info/q
                backoff_in_seconds=10,
            )
        except InvalidBTCAddress:
            # TODO: Move this validation into our own code and before the balance query
            raise InputError(f'The given string {account} is not a valid BTC address')

        return satoshis_to_btc(FVal(btc_resp))  # result is in satoshis

    def query_btc_balances(self) -> None:
        if len(self.accounts.btc) == 0:
            return

        self.balances[A_BTC] = {}
        btc_usd_price = Inquirer().find_usd_price(A_BTC)
        total = FVal(0)
        for account in self.accounts.btc:
            balance = self.query_btc_account_balance(account)
            total += balance
            self.balances[A_BTC][account] = {
                'amount': balance,
                'usd_value': balance * btc_usd_price,
            }

        self.totals[A_BTC] = {'amount': total, 'usd_value': total * btc_usd_price}

    @overload
    @staticmethod
    def _query_token_balances(
            token_asset: EthereumToken,
            query_callback: Callable[[EthereumToken, ChecksumEthAddress], FVal],
            argument: ChecksumEthAddress,
    ) -> FVal:
        ...

    @overload  # noqa: F811
    @staticmethod
    def _query_token_balances(
            token_asset: EthereumToken,
            query_callback: Callable[
                [EthereumToken, List[ChecksumEthAddress]],
                Dict[ChecksumEthAddress, FVal],
            ],
            argument: List[ChecksumEthAddress],
    ) -> Dict[ChecksumEthAddress, FVal]:
        ...

    @staticmethod  # noqa: F811
    def _query_token_balances(
            token_asset: EthereumToken,
            query_callback: Callable,
            argument: Union[List[ChecksumEthAddress], ChecksumEthAddress],
    ) -> Union[FVal, Dict[ChecksumEthAddress, FVal]]:
        """Query tokens by checking the eth_tokens mapping and using the respective query callback.

        The callback is either self.ethchain.get_multitoken_balance or
        self.ethchain.get_token_balance"""
        result = query_callback(
            token_asset,
            argument,
        )

        return result

    def track_new_tokens(self, new_tokens: List[EthereumToken]) -> BlockchainBalancesUpdate:

        intersection = set(new_tokens).intersection(set(self.owned_eth_tokens))
        if intersection != set():
            raise InputError('Some of the new provided tokens to track already exist')

        self.owned_eth_tokens.extend(new_tokens)
        eth_balances = cast(EthBalances, self.balances[A_ETH])

        if eth_balances == {}:
            # if balances have not been yet queried then we should do the entire
            # balance query first in order to create the eth_balances mappings
            self.query_ethereum_balances()
        else:
            # simply update all accounts with any changes adding the token may have
            self.query_ethereum_tokens(
                tokens=new_tokens,
                eth_balances=eth_balances,
            )
        return {'per_account': self.balances, 'totals': self.totals}

    def remove_eth_tokens(self, tokens: List[EthereumToken]) -> BlockchainBalancesUpdate:
        if self.balances[A_ETH] == {}:
            # if balances have not been yet queried then we should do the entire
            # balance query first in order to create the eth_balances mappings
            self.query_ethereum_balances()

        for token in tokens:
            usd_price = Inquirer().find_usd_price(token)
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
            # Remove the token from the totals iff existing. May not exist
            #  if the token price is 0 but is still tracked.
            # See https://github.com/rotki/rotki/issues/467
            # for more details
            self.totals.pop(token, None)
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
        btc_usd_price = Inquirer().find_usd_price(A_BTC)
        remove_with_populated_balance = (
            append_or_remove == 'remove' and len(self.balances[A_BTC]) != 0
        )
        # Query the balance of the account except for the case when it's removed
        # and there is no other account in the balances
        if append_or_remove == 'append' or remove_with_populated_balance:
            balance = self.query_btc_account_balance(account)
            usd_balance = balance * btc_usd_price

        if append_or_remove == 'append':
            self.balances[A_BTC][account] = {'amount': balance, 'usd_value': usd_balance}
        elif append_or_remove == 'remove':
            if account in self.balances[A_BTC][account]:
                del self.balances[A_BTC][account]
        else:
            raise AssertionError('Programmer error: Should be append or remove')

        if len(self.balances[A_BTC]) == 0:
            # If the last account was removed balance should be 0
            self.totals[A_BTC]['amount'] = FVal(0)
            self.totals[A_BTC]['usd_value'] = FVal(0)
        else:
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
            given_account: EthAddress,
            append_or_remove: str,
            add_or_sub: Callable[[FVal, FVal], FVal],
    ) -> None:
        """Either appends or removes an ETH acccount.

        Call with 'append', operator.add to add the account
        Call with 'remove', operator.sub to remove the account
        """
        # Make sure account goes into web3.py as a properly checksummed address
        try:
            account = to_checksum_address(given_account)
        except ValueError:
            raise InputError(f'The given string {given_account} is not a valid ETH address')
        eth_usd_price = Inquirer().find_usd_price(A_ETH)
        remove_with_populated_balance = (
            append_or_remove == 'remove' and len(self.balances[A_ETH]) != 0
        )
        # Query the balance of the account except for the case when it's removed
        # and there is no other account in the balances
        if append_or_remove == 'append' or remove_with_populated_balance:
            balance = self.ethchain.get_eth_balance(account)
            usd_balance = balance * eth_usd_price

        if append_or_remove == 'append':
            self.accounts.eth.append(account)
            self.balances[A_ETH][account] = {A_ETH: balance, 'usd_value': usd_balance}
        elif append_or_remove == 'remove':
            if account not in self.accounts.eth:
                raise InputError('Tried to remove a non existing ETH account')
            self.accounts.eth.remove(account)
            if account in self.balances[A_ETH]:
                del self.balances[A_ETH][account]
        else:
            raise AssertionError('Programmer error: Should be append or remove')

        if len(self.balances[A_ETH]) == 0:
            # If the last account was removed balance should be 0
            self.totals[A_ETH]['amount'] = FVal(0)
            self.totals[A_ETH]['usd_value'] = FVal(0)
        else:
            self.totals[A_ETH]['amount'] = add_or_sub(
                self.totals[A_ETH].get('amount', FVal(0)),
                balance,
            )
            self.totals[A_ETH]['usd_value'] = add_or_sub(
                self.totals[A_ETH].get('usd_value', FVal(0)),
                usd_balance,
            )

        for token in self.owned_eth_tokens:
            usd_price = Inquirer().find_usd_price(token)
            if usd_price == 0:
                # skip tokens that have no price
                continue

            if append_or_remove == 'remove' and token not in self.totals:
                # If we remove an account, and the token has no totals entry skip
                continue

            token_balance = Blockchain._query_token_balances(
                token_asset=token,
                query_callback=self.ethchain.get_token_balance,
                argument=account,
            )
            if token_balance == 0:
                continue

            usd_value = token_balance * usd_price
            if append_or_remove == 'append':
                account_balance = self.balances[A_ETH][account]
                account_balance[token] = token_balance
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

    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: List[BlockchainAddress],
    ) -> Tuple[BlockchainBalancesUpdate, List[BlockchainAddress], str]:
        """Adds new blockchain accounts and requeries all balances after the addition.

        Returns the new total balances, the actually added accounts (some
        accounts may have been invalid) and also any errors that occured
        during the addition.

        May Raise:
        - EthSyncError from modify_blockchain_account
        - InputError if the given accounts list is empty
        """
        if len(accounts) == 0:
            raise InputError('Empty list of blockchain accounts to add was given')

        # If no blockchain query has happened before then we need to query the relevant
        # chain to populate the self.balances mapping
        if str(blockchain) not in self.balances:
            self.query_balances(blockchain)

        added_accounts = []
        full_msg = ''

        for account in accounts:
            try:
                result = self.modify_blockchain_account(
                    blockchain=blockchain,
                    account=account,
                    append_or_remove='append',
                    add_or_sub=operator.add,
                )
                added_accounts.append(account)
            except InputError as e:
                full_msg += str(e)
                result = {'per_account': self.balances, 'totals': self.totals}

        return result, added_accounts, full_msg

    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: List[BlockchainAddress],
    ) -> Tuple[BlockchainBalancesUpdate, List[BlockchainAddress], str]:
        """Removes blockchain accounts and requeries all balances after the removal.

        Returns the new total balances, the actually removes accounts (some
        accounts may have been invalid) and also any errors that occured
        during the removal.

        May Raise:
        - EthSyncError from modify_blockchain_account
        - InputError if the given accounts list is empty
        """
        if len(accounts) == 0:
            raise InputError('Empty list of blockchain accounts to add was given')

        # If no blockchain query has happened before then we need to query the relevant
        # chain to populate the self.balances mapping. But query has to happen after
        # account removal so as not to query unneeded accounts
        balances_queried_before = True
        if str(blockchain) not in self.balances:
            balances_queried_before = False

        removed_accounts = []
        full_msg = ''
        for account in accounts:
            try:
                self.modify_blockchain_account(
                    blockchain=blockchain,
                    account=account,
                    append_or_remove='remove',
                    add_or_sub=operator.sub,
                )
                removed_accounts.append(account)
            except InputError as e:
                full_msg += '. ' + str(e)

        if not balances_queried_before:
            self.query_balances(blockchain)

        result: BlockchainBalancesUpdate = {'per_account': self.balances, 'totals': self.totals}

        return result, removed_accounts, full_msg

    def modify_blockchain_account(
            self,
            blockchain: SupportedBlockchain,
            account: BlockchainAddress,
            append_or_remove: str,
            add_or_sub: Callable[[FVal, FVal], FVal],
    ) -> BlockchainBalancesUpdate:
        """Add or remove a blockchain account

        May raise:

        - InputError if accounts to remove do not exist or if the ethereum/BTC
          addresses are not valid.
        - EthSyncError if there is a problem querying the ethereum chain
        """
        if blockchain == SupportedBlockchain.BITCOIN:
            if append_or_remove == 'remove' and account not in self.accounts.btc:
                raise InputError('Tried to remove a non existing BTC account')

            # above we check that account is a BTC account
            self.modify_btc_account(
                BTCAddress(account),
                append_or_remove,
                add_or_sub,
            )

        elif blockchain == SupportedBlockchain.ETHEREUM:
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
            # That should not happen. Should be checked by marshmallow
            raise AssertionError(
                'Unsupported blockchain {} provided at remove_blockchain_account'.format(
                    blockchain),
            )

        return {'per_account': self.balances, 'totals': self.totals}

    def query_ethereum_tokens(
            self,
            tokens: List[EthereumToken],
            eth_balances: EthBalances,
    ) -> None:
        token_balances = {}
        token_usd_price = {}
        for token in tokens:
            usd_price = Inquirer().find_usd_price(token)
            if usd_price == 0:
                # skip tokens that have no price
                continue
            token_usd_price[token] = usd_price

            token_balances[token] = Blockchain._query_token_balances(
                token_asset=token,
                query_callback=self.ethchain.get_multitoken_balance,
                argument=self.accounts.eth,
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
        eth_usd_price = Inquirer().find_usd_price(A_ETH)
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
