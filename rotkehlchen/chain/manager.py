import logging
import operator
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union, overload

import gevent
import requests
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.aave import Aave
from rotkehlchen.chain.ethereum.makerdao import MakerDAODSR, MakerDAOVaults
from rotkehlchen.chain.ethereum.tokens import EthTokens
from rotkehlchen.chain.ethereum.zerion import DefiProtocolBalances, Zerion
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.errors import EthSyncError, InputError, RemoteError, UnableToDecryptRemoteData
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.typing import (
    BTCAddress,
    ChecksumEthAddress,
    ListOfBlockchainAddresses,
    ModuleName,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import (
    CacheableObject,
    EthereumModule,
    LockableQueryObject,
    cache_response_timewise,
    protect_with_lock,
)
from rotkehlchen.utils.misc import request_get, request_get_dict, satoshis_to_btc, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFI_BALANCES_REQUERY_SECONDS = 600


class AccountAction(Enum):
    QUERY = 1
    APPEND = 2
    REMOVE = 3


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
    eth: EthBalances = field(default_factory=dict)
    btc: Dict[BTCAddress, Balance] = field(default_factory=dict)

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

        blockchain_balances: Dict[str, Dict] = {}
        if eth_balances != {}:
            blockchain_balances['ETH'] = eth_balances
        if btc_balances != {}:
            blockchain_balances['BTC'] = btc_balances
        return blockchain_balances

    def is_queried(self, blockchain: SupportedBlockchain) -> bool:
        if blockchain == SupportedBlockchain.ETHEREUM:
            return self.eth != {}
        elif blockchain == SupportedBlockchain.BITCOIN:
            return self.btc != {}

        raise AssertionError('Invalid blockchain value')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class BlockchainBalancesUpdate:
    per_account: BlockchainBalances
    totals: Totals

    def serialize(self) -> Dict[str, Dict]:
        return {
            'per_account': self.per_account.serialize(),
            'totals': {
                asset: balance.serialize()
                for asset, balance in self.totals.items() if balance != {}
            },
        }


class ChainManager(CacheableObject, LockableQueryObject):

    def __init__(
            self,
            blockchain_accounts: BlockchainAccounts,
            ethereum_manager: 'EthereumManager',
            msg_aggregator: MessagesAggregator,
            database: DBHandler,
            greenlet_manager: GreenletManager,
            premium: Optional[Premium],
            eth_modules: Optional[List[str]] = None,
    ):
        log.debug('Initializing ChainManager')
        super().__init__()
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.accounts = blockchain_accounts

        self.defi_balances_last_query_ts = Timestamp(0)
        self.defi_balances: Dict[ChecksumEthAddress, List[DefiProtocolBalances]] = {}
        # Per account balances
        self.balances = BlockchainBalances()
        # Per asset total balances
        self.totals: Totals = defaultdict(Balance)
        # TODO: Perhaps turn this mapping into a typed dict?
        self.eth_modules: Dict[str, EthereumModule] = {}
        if eth_modules:
            for given_module in eth_modules:
                if given_module == 'makerdao_dsr':
                    self.eth_modules['makerdao_dsr'] = MakerDAODSR(
                        ethereum_manager=ethereum_manager,
                        database=self.database,
                        premium=premium,
                        msg_aggregator=msg_aggregator,
                    )
                elif given_module == 'makerdao_vaults':
                    self.eth_modules['makerdao_vaults'] = MakerDAOVaults(
                        ethereum_manager=ethereum_manager,
                        database=self.database,
                        premium=premium,
                        msg_aggregator=msg_aggregator,
                    )
                elif given_module == 'aave':
                    self.eth_modules['aave'] = Aave(
                        ethereum_manager=ethereum_manager,
                        database=self.database,
                        premium=premium,
                        msg_aggregator=msg_aggregator,
                    )
                else:
                    log.error(f'Unrecognized module value {given_module} given. Skipping...')

        self.greenlet_manager = greenlet_manager

        for name, module in self.eth_modules.items():
            self.greenlet_manager.spawn_and_track(
                task_name=f'startup of {name}',
                method=module.on_startup,
            )

        # Since Zerion initialization needs a few ENS calls we do it asynchronously
        self.zerion: Optional[Zerion] = None
        self.greenlet_manager.spawn_and_track(
            task_name='Initialize Zerion object',
            method=self._initialize_zerion,
        )

    def _initialize_zerion(self):
        self.zerion = Zerion(ethereum_manager=self.ethereum, msg_aggregator=self.msg_aggregator)

    def get_zerion(self) -> Zerion:
        """Returns the initialized zerion. If it's not ready it waits for 5 seconds
        and then times out. This should really never happen

        May raise:
        - gevent.Timeout if no result is returned within 5 seconds
        """
        if self.zerion is not None:
            return self.zerion

        with gevent.Timeout(5):
            while True:
                if self.zerion is None:
                    gevent.sleep(0.5)
                else:
                    return self.zerion

    def __del__(self) -> None:
        del self.ethereum

    def set_eth_rpc_endpoint(self, endpoint: str) -> Tuple[bool, str]:
        return self.ethereum.set_rpc_endpoint(endpoint)

    def deactivate_premium_status(self) -> None:
        dsr = self.makerdao_dsr
        if dsr:
            dsr.premium = None
        vaults = self.makerdao_vaults
        if vaults:
            vaults.premium = None

    @property
    def makerdao_dsr(self) -> Optional[MakerDAODSR]:
        module = self.eth_modules.get('makerdao_dsr', None)
        if not module:
            return None

        return module  # type: ignore

    @property
    def makerdao_vaults(self) -> Optional[MakerDAOVaults]:
        module = self.eth_modules.get('makerdao_vaults', None)
        if not module:
            return None

        return module  # type: ignore

    @property
    def aave(self) -> Optional[Aave]:
        module = self.eth_modules.get('aave', None)
        if not module:
            return None

        return module  # type: ignore

    def queried_addresses_for_module(self, module: ModuleName) -> List[ChecksumEthAddress]:
        """Returns the addresses to query for the given module/protocol"""
        result = QueriedAddresses(self.database).get_queried_addresses_for_module(module)
        return result if result is not None else self.accounts.eth

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
    def query_btc_accounts_balances(accounts: List[BTCAddress]) -> Dict[BTCAddress, FVal]:
        """Queries blockchain.info for the balance of account

        May raise:
        - RemotError if there is a problem querying blockchain.info or blockcypher
        """
        source = 'blockchain.info'
        balances = {}
        try:
            if any(account.lower()[0:3] == 'bc1' for account in accounts):
                # if 1 account is bech32 we have to query blockcypher. blockchaininfo won't work
                source = 'blockcypher.com'
                # the bech32 accounts have to be given lowercase to the
                # blockcypher query. No idea why.
                new_accounts = []
                for x in accounts:
                    lowered = x.lower()
                    if lowered[0:3] == 'bc1':
                        new_accounts.append(lowered)
                    else:
                        new_accounts.append(x)

                # blockcypher's batching takes up as many api queries as the batch,
                # and the api rate limit is 3 requests per second. So we should make
                # sure each batch is of max size 3
                # https://www.blockcypher.com/dev/bitcoin/#batching
                batches = [new_accounts[x: x + 3] for x in range(0, len(new_accounts), 3)]
                total_idx = 0
                for batch in batches:
                    params = ';'.join(batch)
                    url = f'https://api.blockcypher.com/v1/btc/main/addrs/{params}/balance'
                    response_data = request_get(url=url, handle_429=True, backoff_in_seconds=4)

                    if isinstance(response_data, dict):
                        # If only one account was requested put it in a list so the
                        # rest of the code works
                        response_data = [response_data]

                    for idx, entry in enumerate(response_data):
                        # we don't use the returned address as it may be lowercased
                        balances[accounts[total_idx + idx]] = satoshis_to_btc(
                            FVal(entry['final_balance']),
                        )
                    total_idx += len(batch)
            else:
                params = '|'.join(accounts)
                btc_resp = request_get_dict(
                    url=f'https://blockchain.info/multiaddr?active={params}',
                    handle_429=True,
                    # If we get a 429 then their docs suggest 10 seconds
                    # https://blockchain.info/q
                    backoff_in_seconds=10,
                )
                for idx, entry in enumerate(btc_resp['addresses']):
                    balances[accounts[idx]] = satoshis_to_btc(FVal(entry['final_balance']))
        except (requests.exceptions.ConnectionError, UnableToDecryptRemoteData) as e:
            raise RemoteError(f'bitcoin external API request failed due to {str(e)}')
        except KeyError as e:
            raise RemoteError(
                f'Malformed response when querying bitcoin blockchain via {source}.'
                f'Did not find key {e}',
            )

        return balances

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
        balances = self.query_btc_accounts_balances(self.accounts.btc)
        for account, balance in balances.items():
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

        The callback is either self.ethereum.get_multiaccount_token_balance or
        self.ethereum.get_token_balance"""
        result = query_callback(
            token_asset,
            argument,
        )

        return result

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
        - RemotError if there is a problem querying blockchain.info or cryptocompare
        """
        btc_usd_price = Inquirer().find_usd_price(A_BTC)
        remove_with_populated_balance = (
            append_or_remove == 'remove' and len(self.balances.btc) != 0
        )
        # Query the balance of the account except for the case when it's removed
        # and there is no other account in the balances
        if append_or_remove == 'append' or remove_with_populated_balance:
            balances = self.query_btc_accounts_balances([account])
            balance = balances[account]
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
            account: ChecksumEthAddress,
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
        eth_usd_price = Inquirer().find_usd_price(A_ETH)
        remove_with_populated_balance = (
            append_or_remove == 'remove' and len(self.balances.eth) != 0
        )
        # Query the balance of the account except for the case when it's removed
        # and there is no other account in the balances
        if append_or_remove == 'append' or remove_with_populated_balance:
            amount = self.ethereum.get_eth_balance(account)
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

        action = AccountAction.APPEND if append_or_remove == 'append' else AccountAction.REMOVE
        self._query_ethereum_tokens(
            action=action,
            given_accounts=[account],
        )

    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> BlockchainBalancesUpdate:
        """Adds new blockchain accounts and requeries all balances after the addition.
        The accounts are added in the blockchain object and not in the database.
        Returns the new total balances, the actually added accounts (some
        accounts may have been invalid) and also any errors that occured
        during the addition.

        May Raise:
        - EthSyncError from modify_blockchain_accounts
        - InputError if the given accounts list is empty, or if it contains invalid accounts
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem
        """
        if len(accounts) == 0:
            raise InputError('Empty list of blockchain accounts to add was given')

        # If no blockchain query has happened before then we need to query the relevant
        # chain to populate the self.balances mapping.
        if not self.balances.is_queried(blockchain):
            self.query_balances(blockchain, ignore_cache=True)

        result = self.modify_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
            append_or_remove='append',
            add_or_sub=operator.add,
        )

        return result

    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> BlockchainBalancesUpdate:
        """Removes blockchain accounts and requeries all balances after the removal.

        The accounts are removed from the blockchain object and not from the database.
        Returns the new total balances, the actually removes accounts (some
        accounts may have been invalid) and also any errors that occured
        during the removal.

        If any of the given accounts are not known an inputError is raised and
        no account is modified.

        May Raise:
        - EthSyncError from modify_blockchain_accounts
        - InputError if the given accounts list is empty, or if
        it contains an unknown account or invalid account
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem
        """
        if len(accounts) == 0:
            raise InputError('Empty list of blockchain accounts to remove was given')

        unknown_accounts = set(accounts).difference(self.accounts.get(blockchain))
        if len(unknown_accounts) != 0:
            raise InputError(
                f'Tried to remove unknown {blockchain.value} '
                f'accounts {",".join(unknown_accounts)}',
            )

        # If no blockchain query has happened before then we need to query the relevant
        # chain to populate the self.balances mapping. But query has to happen after
        # account removal so as not to query unneeded accounts
        balances_queried_before = True
        if not self.balances.is_queried(blockchain):
            balances_queried_before = False

        self.modify_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
            append_or_remove='remove',
            add_or_sub=operator.sub,
        )

        if not balances_queried_before:
            self.query_balances(blockchain, ignore_cache=True)

        result = self.get_balances_update()
        return result

    def modify_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
            append_or_remove: str,
            add_or_sub: Callable[[FVal, FVal], FVal],
    ) -> BlockchainBalancesUpdate:
        """Add or remove a list of blockchain account

        May raise:

        - InputError if accounts to remove do not exist.
        - EthSyncError if there is a problem querying the ethereum chain
        - RemoteError if there is a problem querying an external service such
          as etherscan or blockchain.info
        """
        if blockchain == SupportedBlockchain.BITCOIN:
            for account in accounts:
                self.modify_btc_account(
                    BTCAddress(account),
                    append_or_remove,
                    add_or_sub,
                )

        elif blockchain == SupportedBlockchain.ETHEREUM:
            zerion = self.get_zerion()
            for account in accounts:
                address = deserialize_ethereum_address(account)
                try:
                    self.modify_eth_account(
                        account=address,
                        append_or_remove=append_or_remove,
                        add_or_sub=add_or_sub,
                    )
                except BadFunctionCallOutput as e:
                    log.error(
                        'Assuming unsynced chain. Got web3 BadFunctionCallOutput '
                        'exception: {}'.format(str(e)),
                    )
                    raise EthSyncError(
                        'Tried to use the ethereum chain of a local client to edit '
                        'an eth account but the chain is not synced.',
                    )

                # Also modify defi balances
                if append_or_remove == 'append':
                    balances = zerion.all_balances_for_account(address)
                    if len(balances) != 0:
                        self.defi_balances[address] = balances
                else:  # remove
                    self.defi_balances.pop(address, None)
                # For each module run the corresponding callback for the address
                for _, module in self.eth_modules.items():
                    if append_or_remove == 'append':
                        module.on_account_addition(address)
                    else:  # remove
                        module.on_account_removal(address)

        else:
            # That should not happen. Should be checked by marshmallow
            raise AssertionError(
                'Unsupported blockchain {} provided at remove_blockchain_account'.format(
                    blockchain),
            )

        return self.get_balances_update()

    def _query_ethereum_tokens(
            self,
            action: AccountAction,
            given_accounts: Optional[List[ChecksumEthAddress]] = None,
    ) -> None:
        """Queries ethereum token balance via either etherscan or ethereum node

        By default queries all accounts but can also be given a specific list of
        accounts to query.

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        if given_accounts is None:
            accounts = self.accounts.eth
        else:
            accounts = given_accounts

        ethtokens = EthTokens(database=self.database, ethereum=self.ethereum)
        try:
            balance_result, token_usd_price = ethtokens.query_tokens_for_addresses(accounts)
        except BadFunctionCallOutput as e:
            log.error(
                'Assuming unsynced chain. Got web3 BadFunctionCallOutput '
                'exception: {}'.format(str(e)),
            )
            raise EthSyncError(
                'Tried to use the ethereum chain of the provided client to query '
                'token balances but the chain is not synced.',
            )

        add_or_sub: Optional[Callable[[Any, Any], Any]]
        if action == AccountAction.APPEND:
            add_or_sub = operator.add
        elif action == AccountAction.REMOVE:
            add_or_sub = operator.sub
        else:
            add_or_sub = None

        # Update the per account token balance and usd value
        token_totals: Dict[EthereumToken, FVal] = defaultdict(FVal)
        eth_balances = self.balances.eth
        for account, token_balances in balance_result.items():
            for token, token_balance in token_balances.items():
                if token_usd_price[token] == ZERO:
                    # skip tokens that have no price
                    continue

                token_totals[token] += token_balance
                if action == AccountAction.QUERY or action == AccountAction.APPEND:
                    usd_value = token_balance * token_usd_price[token]
                    eth_balances[account].asset_balances[token] = Balance(
                        amount=token_balance,
                        usd_value=usd_value,
                    )
                    eth_balances[account].increase_total_usd_value(usd_value)

        # Update the totals
        for token, token_total_balance in token_totals.items():
            if action == AccountAction.QUERY:
                self.totals[token] = Balance(
                    amount=token_total_balance,
                    usd_value=token_total_balance * token_usd_price[token],
                )
            else:
                if action == AccountAction.REMOVE and token not in self.totals:
                    # Removing the only account that holds this token
                    self.totals[token] = Balance(amount=ZERO, usd_value=ZERO)
                else:
                    new_amount = add_or_sub(self.totals[token].amount, token_total_balance)  # type: ignore  # noqa: E501
                    if new_amount <= ZERO:
                        new_amount = ZERO
                        new_usd_value = ZERO
                    else:
                        new_usd_value = add_or_sub(  # type: ignore
                            self.totals[token].usd_value,
                            token_total_balance * token_usd_price[token],
                        )
                    self.totals[token] = Balance(
                        amount=new_amount,
                        usd_value=new_usd_value,
                    )

    def query_ethereum_tokens(self) -> None:
        """Queries the ethereum token balances and populates the state

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        # Clear out all previous token balances. If token is "tracked" via the owned
        # tokens just zero out its balance
        for token in [x for x, _ in self.totals.items() if isinstance(x, EthereumToken)]:
            del self.totals[token]
        self._query_ethereum_tokens(action=AccountAction.QUERY)

        # If we have anything in DSR also count it towards total blockchain balances
        eth_balances = self.balances.eth
        if self.makerdao_dsr:
            additional_total = Balance()
            current_dsr_report = self.makerdao_dsr.get_current_dsr()
            for dsr_account, balance_entry in current_dsr_report.balances.items():

                if balance_entry.amount == ZERO:
                    continue

                if A_DAI not in eth_balances[dsr_account].asset_balances:
                    eth_balances[dsr_account].asset_balances[A_DAI] = Balance()

                eth_balances[dsr_account].asset_balances[A_DAI] += balance_entry
                eth_balances[dsr_account].increase_total_usd_value(balance_entry.usd_value)
                additional_total += balance_entry

            if additional_total.amount != ZERO:
                self.totals[A_DAI] += additional_total

    def query_defi_balances(self) -> Dict[ChecksumEthAddress, List[DefiProtocolBalances]]:
        """Queries DeFi balances from Zerion contract and updates the state

        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        if ts_now() - self.defi_balances_last_query_ts < DEFI_BALANCES_REQUERY_SECONDS:
            return self.defi_balances

        # query zerion for defi balances
        self.defi_balances = {}
        zerion = self.get_zerion()
        for account in self.accounts.eth:
            balances = zerion.all_balances_for_account(account)
            if len(balances) != 0:
                self.defi_balances[account] = balances

        self.defi_balances_last_query_ts = ts_now()
        return self.defi_balances

    def query_ethereum_balances(self) -> None:
        """Queries all the ethereum balances and populates the state

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        if len(self.accounts.eth) == 0:
            return

        # Query ethereum ETH balances
        eth_accounts = self.accounts.eth
        eth_usd_price = Inquirer().find_usd_price(A_ETH)
        balances = self.ethereum.get_multieth_balance(eth_accounts)
        eth_total = FVal(0)
        for account, balance in balances.items():
            eth_total += balance
            usd_value = balance * eth_usd_price
            self.balances.eth[account] = EthereumAccountBalance(
                start_eth_amount=balance,
                start_eth_usd_value=usd_value,
            )

        self.totals[A_ETH] = Balance(amount=eth_total, usd_value=eth_total * eth_usd_price)

        self.query_defi_balances()
        self.query_ethereum_tokens()
        vaults_module = self.makerdao_vaults
        if vaults_module is not None:
            normalized_balances = vaults_module.get_normalized_balances()
            for asset, normalized_vault_balance in normalized_balances.items():
                self.totals[asset] += normalized_vault_balance
