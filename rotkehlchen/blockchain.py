import logging
import operator
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union, overload

import requests
from dataclasses import dataclass
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


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class Balance:
    amount: FVal = ZERO
    usd_value: FVal = ZERO

    def serialize(self) -> Dict[str, str]:
        return {'amount': str(self.amount), 'usd_value': str(self.usd_value)}


Totals = Dict[Asset, Balance]


@dataclass(init=False, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EthereumAccountBalance:
    asset_balances: Dict[Asset, Balance]
    total_usd_value: FVal

    def __init__(self, start_eth_amount: FVal, start_eth_usd_value: FVal):
        self.asset_balances = {
            A_ETH: Balance(amount=start_eth_amount, usd_value=start_eth_usd_value),
        }
        self.total_usd_value = start_eth_usd_value

    def increase_total_usd_value(self, amount: FVal) -> None:
        self.total_usd_value += amount

    def decrease_total_usd_value(self, amount: FVal) -> None:
        self.total_usd_value -= amount


EthBalances = Dict[ChecksumEthAddress, EthereumAccountBalance]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BlockchainBalances:
    eth: EthBalances = {}
    btc: Dict[BTCAddress, Balance] = {}

    def serialize(self) -> Dict[str, Dict]:
        eth_balances: Dict[ChecksumEthAddress, Dict] = {}
        for account, ethereum_balance in self.eth.items():
            eth_balances[account] = {}
            eth_balances[account]['assets'] = {}
            for asset, balance_entry in ethereum_balance.asset_balances.items():
                eth_balances[account]['assets'][asset.identifier] = balance_entry.serialize()
            eth_balances[account]['total_usd_value'] = str(ethereum_balance.total_usd_value)

        btc_balances: Dict[BTCAddress, Dict] = {}
        for btc_account, balances in self.btc.items():
            btc_balances[btc_account] = balances.serialize()

        return {'ETH': eth_balances, 'BTC': btc_balances}

    def is_queried(self, blockchain: SupportedBlockchain) -> bool:
        if blockchain == SupportedBlockchain.ETHEREUM:
            return self.eth == {}
        elif blockchain == SupportedBlockchain.BITCOIN:
            return self.btc == {}

        raise AssertionError('Invalid blockchain value')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class BlockchainBalancesUpdate:
    per_account: BlockchainBalances
    totals: Totals

    def serialize(self) -> Dict[str, Dict]:
        return {'per_account': self.per_account.serialize(), 'totals': self.totals}


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
        self.balances = BlockchainBalances()
        # Per asset total balances
        self.totals: Totals = defaultdict(Balance)

    def __del__(self) -> None:
        del self.ethchain

    def set_eth_rpc_endpoint(self, endpoint: str) -> Tuple[bool, str]:
        return self.ethchain.set_rpc_endpoint(endpoint)

    @property
    def eth_tokens(self) -> List[EthereumToken]:
        return self.owned_eth_tokens

    def get_balances_update(self) -> BlockchainBalancesUpdate:
        return BlockchainBalancesUpdate(per_account=self.balances, totals=self.totals)

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(
            self,  # pylint: disable=unused-argument
            blockchain: Optional[SupportedBlockchain] = None,
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> BlockchainBalancesUpdate:
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
        if should_query_btc:
            self.query_btc_balances()

        return self.get_balances_update()

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

        self.balances.btc = {}
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
            self.balances.btc[account] = Balance(
                amount=balance,
                usd_value=balance * btc_usd_price,
            )

        self.totals[A_BTC] = Balance(amount=total, usd_value=total * btc_usd_price)

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
        if self.balances.eth == {}:
            # if balances have not been yet queried then we should do the entire
            # balance query first in order to create the eth_balances mappings
            self.query_ethereum_balances()
        else:
            # simply update all accounts with any changes adding the token may have
            self.query_ethereum_tokens(
                tokens=new_tokens,
            )
        return self.get_balances_update()

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
        if self.balances.eth == {}:
            # if balances have not been yet queried then we should do the entire
            # balance query first in order to create the eth_balances mappings
            self.query_ethereum_balances()

        for token in tokens:
            usd_price = Inquirer().find_usd_price(token)
            for account, account_data in self.balances.eth.items():
                if token not in account_data.asset_balances:
                    continue

                amount = account_data.asset_balances[token].amount
                deleting_usd_value = amount * usd_price
                del self.balances.eth[account].asset_balances[token]
                self.balances.eth[account].decrease_total_usd_value(deleting_usd_value)

            # Remove the token from the totals iff existing. May not exist
            # if the token price is 0 but is still tracked.
            # See https://github.com/rotki/rotki/issues/467
            # for more details
            self.totals.pop(token, None)
            self.owned_eth_tokens.remove(token)

        return self.get_balances_update()

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
            append_or_remove == 'remove' and len(self.balances.btc) != 0
        )
        # Query the balance of the account except for the case when it's removed
        # and there is no other account in the balances
        if append_or_remove == 'append' or remove_with_populated_balance:
            balance = self.query_btc_account_balance(account)
            usd_balance = balance * btc_usd_price

        if append_or_remove == 'append':
            self.balances.btc[account] = Balance(amount=balance, usd_value=usd_balance)
        elif append_or_remove == 'remove':
            if account in self.balances.btc:
                del self.balances.btc[account]
        else:
            raise AssertionError('Programmer error: Should be append or remove')

        if len(self.balances.btc) == 0:
            # If the last account was removed balance should be 0
            self.totals[A_BTC].amount = ZERO
            self.totals[A_BTC].usd_value = ZERO
        else:
            self.totals[A_BTC].amount = add_or_sub(self.totals[A_BTC].amount, balance)
            self.totals[A_BTC].usd_value = add_or_sub(self.totals[A_BTC].usd_value, usd_balance)

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
            append_or_remove == 'remove' and len(self.balances.eth) != 0
        )
        # Query the balance of the account except for the case when it's removed
        # and there is no other account in the balances
        if append_or_remove == 'append' or remove_with_populated_balance:
            amount = self.ethchain.get_eth_balance(account)
            usd_value = amount * eth_usd_price

        if append_or_remove == 'append':
            self.accounts.eth.append(account)
            self.balances.eth[account] = EthereumAccountBalance(
                start_eth_amount=amount,
                start_eth_usd_value=usd_value,
            )
        elif append_or_remove == 'remove':
            if account not in self.accounts.eth:
                raise InputError('Tried to remove a non existing ETH account')
            self.accounts.eth.remove(account)
            if account in self.balances.eth:
                del self.balances.eth[account]
        else:
            raise AssertionError('Programmer error: Should be append or remove')

        if len(self.balances.eth) == 0:
            # If the last account was removed balance should be 0
            self.totals[A_ETH].amount = ZERO
            self.totals[A_ETH].usd_value = ZERO
        else:
            self.totals[A_ETH].amount = add_or_sub(self.totals[A_ETH].amount, amount)
            self.totals[A_ETH].usd_value = add_or_sub(self.totals[A_ETH].usd_value, usd_value)

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
                eth_acc = self.balances.eth[account]
                eth_acc.asset_balances[token] = Balance(amount=token_balance, usd_value=usd_value)
                eth_acc.increase_total_usd_value(usd_value)

            self.totals[token] = Balance(
                amount=add_or_sub(self.totals[token].amount, token_balance),
                usd_value=add_or_sub(self.totals[token].usd_value, usd_value),
            )

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
        if not self.balances.is_queried(blockchain):
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
                result = self.get_balances_update()

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
        if not self.balances.is_queried(blockchain):
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

        result = self.get_balances_update()
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

        return self.get_balances_update()

    def query_ethereum_tokens(
            self,
            tokens: List[EthereumToken],
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

        eth_balances = self.balances.eth
        for token, token_accounts in token_balances.items():
            token_total = ZERO
            for account, balance in token_accounts.items():
                token_total += balance
                usd_value = balance * token_usd_price[token]
                if balance != ZERO:
                    eth_balances[account].asset_balances[token] = Balance(
                        amount=balance,
                        usd_value=usd_value,
                    )
                    eth_balances[account].increase_total_usd_value(usd_value)

            self.totals[token] = Balance(
                amount=token_total,
                usd_value=token_total * token_usd_price[token],
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
        for account, balance in balances.items():
            eth_total += balance
            usd_value = balance * eth_usd_price
            self.balances.eth[account] = EthereumAccountBalance(
                start_eth_amount=balance,
                start_eth_usd_value=usd_value,
            )

        self.totals[A_ETH] = Balance(amount=eth_total, usd_value=eth_total * eth_usd_price)
        # And now also query tokens to complete the picture
        self.query_ethereum_tokens(self.owned_eth_tokens)
