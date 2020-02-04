import logging
import operator
from collections import defaultdict
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union, cast, overload

import requests
from eth_utils.address import to_checksum_address
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.errors import (
    EthSyncError,
    InputError,
    InvalidBTCAddress,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import (
    BlockchainAddress,
    BTCAddress,
    ChecksumEthAddress,
    EthAddress,
    ListOfBlockchainAddresses,
    Price,
    SupportedBlockchain,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import (
    CacheableObject,
    LockableQueryObject,
    cache_response_timewise,
    protect_with_lock,
)
from rotkehlchen.utils.misc import request_get_direct, satoshis_to_btc

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
EthBalances = Dict[ChecksumEthAddress, Dict[str, Union[Dict[Asset, Dict[str, FVal]], FVal]]]


class Blockchain(CacheableObject, LockableQueryObject):

    def __init__(
            self,
            blockchain_accounts: BlockchainAccounts,
            owned_eth_tokens: List[EthereumToken],
            ethchain: 'Ethchain',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__()
        self.ethchain = ethchain
        self.msg_aggregator = msg_aggregator
        self.owned_eth_tokens = owned_eth_tokens
        self.accounts = blockchain_accounts

        # Per account balances
        self.balances: Balances = defaultdict(dict)
        # Per asset total balances
        self.totals: Totals = defaultdict(dict)

    def __del__(self) -> None:
        del self.ethchain

    def set_eth_rpc_endpoint(self, endpoint: str) -> Tuple[bool, str]:
        return self.ethchain.set_rpc_endpoint(endpoint)

    @property
    def eth_tokens(self) -> List[EthereumToken]:
        return self.owned_eth_tokens

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(
            self,  # pylint: disable=unused-argument
            blockchain: Optional[SupportedBlockchain] = None,
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> Dict[str, Dict]:
        """Queries either all, or specific blockchain balances

        May raise:
        - RemoteError if an external service such as Etherscan or blockchain.info
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        should_query_eth = not blockchain or blockchain == SupportedBlockchain.ETHEREUM
        should_query_btc = not blockchain or blockchain == SupportedBlockchain.BITCOIN

        if should_query_eth:
            self.query_ethereum_balances()

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

        return {'per_account': per_account, 'totals': totals}

    @staticmethod
    def query_btc_account_balance(account: BTCAddress) -> FVal:
        """Queries blockchain.info for the balance of account

        May raise:
        - InputError if the given account is not a valid BTC address
        - RemotError if there is a problem querying blockchain.info
        """
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
        except (requests.exceptions.ConnectionError, UnableToDecryptRemoteData) as e:
            raise RemoteError(f'blockchain.info API request failed due to {str(e)}')

        return satoshis_to_btc(FVal(btc_resp))  # result is in satoshis

    def query_btc_balances(self) -> None:
        """Queries blockchain.info for the balance of all BTC accounts

        May raise:
        - RemotError if there is a problem querying blockchain.info or cryptocompare
        """
        if len(self.accounts.btc) == 0:
            return

        self.balances[A_BTC] = {}
        btc_usd_price = Inquirer().find_usd_price(A_BTC)
        total = FVal(0)
        for account in self.accounts.btc:
            try:
                balance = self.query_btc_account_balance(account)
            except InputError:
                # This should really never happen.
                self.msg_aggregator.add_error(
                    f'While querying BTC balances found invalid BTC account {account} in the DB',
                )
                continue
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
        """
        Adds new_tokens to the state and tracks their balance for each account.

        May raise:
        - InputError if some of the tokens already exist
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
          client and the chain is not synced
        """

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
        """
        Removes tokens from the state and stops their balance from being tracked
        for each account

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        if self.balances[A_ETH] == {}:
            # if balances have not been yet queried then we should do the entire
            # balance query first in order to create the eth_balances mappings
            self.query_ethereum_balances()

        for token in tokens:
            usd_price = Inquirer().find_usd_price(token)
            for account, account_data in self.balances[A_ETH].items():
                if token not in account_data['assets']:  # type: ignore
                    continue

                balance = account_data['assets'][token]['amount']  # type: ignore
                deleting_usd_value = balance * usd_price
                del self.balances[A_ETH][account]['assets'][token]  # type: ignore
                self.balances[A_ETH][account]['total_usd_value'] = (
                    self.balances[A_ETH][account]['total_usd_value'] -
                    deleting_usd_value
                )
            # Remove the token from the totals iff existing. May not exist
            # if the token price is 0 but is still tracked.
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

        May raise:
        - InputError if the given account is not a valid BTC address
        - RemotError if there is a problem querying blockchain.info or cryptocompare
        """
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
            if account in self.balances[A_BTC]:
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
        # At the very end add/remove it from the accounts
        getattr(self.accounts.btc, append_or_remove)(account)

    def modify_eth_account(
            self,
            given_account: EthAddress,
            append_or_remove: str,
            add_or_sub: Callable[[FVal, FVal], FVal],
    ) -> None:
        """Either appends or removes an ETH acccount.

        Call with 'append', operator.add to add the account
        Call with 'remove', operator.sub to remove the account

        May raise:
        - Input error if the given_account is not a valid ETH address
        - BadFunctionCallOutput if a token is queried from a local chain
        and the chain is not synced
        - RemoteError if there is a problem with a query to an external
        service such as Etherscan or cryptocompare
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
            self.balances[A_ETH][account] = {
                'assets': {  # type: ignore
                    A_ETH: {'amount': balance, 'usd_value': usd_balance},
                },
                'total_usd_value': usd_balance,
            }
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
            try:
                usd_price = Inquirer().find_usd_price(token)
            except RemoteError:
                usd_price = Price(ZERO)
            if usd_price == ZERO:
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
                account_balance['assets'][token] = {'amount': token_balance, 'usd_value': usd_value}  # type: ignore  # noqa: E501
                account_balance['total_usd_value'] = account_balance['total_usd_value'] + usd_value

            self.totals[token] = {
                'amount': add_or_sub(
                    self.totals[token].get('amount', ZERO),
                    token_balance,
                ),
                'usd_value': add_or_sub(
                    self.totals[token].get('usd_value', ZERO),
                    usd_value,
                ),
            }

    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> Tuple[BlockchainBalancesUpdate, ListOfBlockchainAddresses, str]:
        """Adds new blockchain accounts and requeries all balances after the addition.
        The accounts are added in the blockchain object and not in the database.
        Returns the new total balances, the actually added accounts (some
        accounts may have been invalid) and also any errors that occured
        during the addition.

        May Raise:
        - EthSyncError from modify_blockchain_account
        - InputError if the given accounts list is empty
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem
        """
        if len(accounts) == 0:
            raise InputError('Empty list of blockchain accounts to add was given')

        # If no blockchain query has happened before then we need to query the relevant
        # chain to populate the self.balances mapping.
        if blockchain.value not in self.balances:
            self.query_balances(blockchain, ignore_cache=True)

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

        # Ignore type checks here. added_accounts is the same type as accounts
        # but not sure how to show that to mypy
        return result, added_accounts, full_msg  # type: ignore

    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> Tuple[BlockchainBalancesUpdate, ListOfBlockchainAddresses, str]:
        """Removes blockchain accounts and requeries all balances after the removal.

        The accounts are removed from the blockchain object and not from the database.
        Returns the new total balances, the actually removes accounts (some
        accounts may have been invalid) and also any errors that occured
        during the removal.

        May Raise:
        - EthSyncError from modify_blockchain_account
        - InputError if the given accounts list is empty
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem
        """
        if len(accounts) == 0:
            raise InputError('Empty list of blockchain accounts to add was given')

        # If no blockchain query has happened before then we need to query the relevant
        # chain to populate the self.balances mapping. But query has to happen after
        # account removal so as not to query unneeded accounts
        balances_queried_before = True
        if blockchain.value not in self.balances:
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
            self.query_balances(blockchain, ignore_cache=True)

        result: BlockchainBalancesUpdate = {'per_account': self.balances, 'totals': self.totals}

        # Ignore type checks here. removed_accounts is the same type as accounts
        # but not sure how to show that to mypy
        return result, removed_accounts, full_msg  # type: ignore

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
        - RemoteError if there is a problem querying an external service such
          as etherscan or blockchain.info
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
        """Queries the ethereum token balances and populates the state

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        token_balances = {}
        token_usd_price = {}
        for token in tokens:
            try:
                usd_price = Inquirer().find_usd_price(token)
            except RemoteError:
                usd_price = Price(ZERO)
            if usd_price == ZERO:
                # skip tokens that have no price
                continue
            token_usd_price[token] = usd_price

            try:
                token_balances[token] = Blockchain._query_token_balances(
                    token_asset=token,
                    query_callback=self.ethchain.get_multitoken_balance,
                    argument=self.accounts.eth,
                )
            except BadFunctionCallOutput as e:
                log.error(
                    'Assuming unsynced chain. Got web3 BadFunctionCallOutput '
                    'exception: {}'.format(str(e)),
                )
                raise EthSyncError(
                    'Tried to use the ethereum chain of the provided client to query '
                    'token balances but the chain is not synced.',
                )

        for token, token_accounts in token_balances.items():
            token_total = FVal(0)
            for account, balance in token_accounts.items():
                token_total += balance
                usd_value = balance * token_usd_price[token]
                if balance != ZERO:
                    eth_balances[account]['assets'][token] = {  # type: ignore
                        'amount': balance,
                        'usd_value': usd_value,
                    }
                    eth_balances[account]['total_usd_value'] = (
                        eth_balances[account]['total_usd_value'] + usd_value  # type: ignore
                    )

            self.totals[token] = {
                'amount': token_total,
                'usd_value': token_total * token_usd_price[token],
            }

        self.balances[A_ETH] = cast(
            Dict[BlockchainAddress, Dict[Union[str, Asset], FVal]],
            eth_balances,
        )

    def query_ethereum_balances(self) -> None:
        """Queries the ethereum balances and populates the state

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        if len(self.accounts.eth) == 0:
            return

        eth_accounts = self.accounts.eth
        eth_usd_price = Inquirer().find_usd_price(A_ETH)
        balances = self.ethchain.get_multieth_balance(eth_accounts)
        eth_total = FVal(0)
        eth_balances: EthBalances = {}
        for account, balance in balances.items():
            eth_total += balance
            usd_value = balance * eth_usd_price
            eth_balances[account] = {
                'assets': {
                    A_ETH: {'amount': balance, 'usd_value': usd_value},
                },
                'total_usd_value': usd_value,
            }

        self.totals[A_ETH] = {'amount': eth_total, 'usd_value': eth_total * eth_usd_price}
        # but they are not complete until token query
        self.balances[A_ETH] = cast(
            Dict[BlockchainAddress, Dict[Union[str, Asset], FVal]],
            eth_balances,
        )

        # And now for tokens
        self.query_ethereum_tokens(self.owned_eth_tokens, eth_balances)
