import logging
import operator
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

import gevent
from gevent.lock import Semaphore
from typing_extensions import Literal
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.accounting.structures import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.bitcoin import get_bitcoin_addresses_balances
from rotkehlchen.chain.ethereum.aave import Aave
from rotkehlchen.chain.ethereum.compound import Compound
from rotkehlchen.chain.ethereum.eth2 import (
    get_eth2_balances,
    get_eth2_balances_via_deposits,
    get_eth2_staking_deposits,
)
from rotkehlchen.chain.ethereum.makerdao import MakerDAODSR, MakerDAOVaults
from rotkehlchen.chain.ethereum.tokens import EthTokens
from rotkehlchen.chain.ethereum.uniswap import Uniswap
from rotkehlchen.chain.ethereum.yearn import YearnVaults
from rotkehlchen.chain.ethereum.zerion import DefiProtocolBalances, Zerion
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_ETH2
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.errors import EthSyncError, InputError, UnknownAsset
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
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.externalapis.beaconchain import BeaconChain

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFI_BALANCES_REQUERY_SECONDS = 600

# Mapping to token symbols to ignore. True means all
DEFI_PROTOCOLS_TO_SKIP_ASSETS = {
    # aTokens are already detected at token balance queries
    'Aave': True,  # True means all
    # cTokens are already detected at token balance queries
    'Compound': True,  # True means all
    # Chitoken is in our all_assets.json
    'Chi Gastoken by 1inch': True,  # True means all
    # yearn vault balances are detected by the yTokens
    'yearn.finance • Vaults': True,  # True means all
    # Synthetix SNX token is in all_assets.json
    'Synthetix': ['SNX'],
    # Ampleforth's AMPL token is in all_assets.json
    'Ampleforth': ['AMPL'],
}


T = TypeVar('T')
AddOrSub = Callable[[T, T], T]


class AccountAction(Enum):
    QUERY = 1
    APPEND = 2
    REMOVE = 3


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BlockchainBalances:
    db: DBHandler  # Need this to serialize BTC accounts with xpub mappings
    eth: DefaultDict[ChecksumEthAddress, BalanceSheet] = field(init=False)
    btc: Dict[BTCAddress, Balance] = field(init=False)

    def __post_init__(self) -> None:
        self.eth = defaultdict(BalanceSheet)
        self.btc = defaultdict(Balance)

    def serialize(self) -> Dict[str, Dict]:
        eth_balances = {k: v.serialize() for k, v in self.eth.items()}
        btc_balances: Dict[str, Any] = {}
        xpub_mappings = self.db.get_addresses_to_xpub_mapping(list(self.btc.keys()))
        for btc_account, balances in self.btc.items():
            xpub_result = xpub_mappings.get(btc_account, None)
            if xpub_result is None:
                if 'standalone' not in btc_balances:
                    btc_balances['standalone'] = {}

                addresses_dict = btc_balances['standalone']
            else:
                if 'xpubs' not in btc_balances:
                    btc_balances['xpubs'] = []

                addresses_dict = None
                for xpub_entry in btc_balances['xpubs']:
                    found = (
                        xpub_result.xpub.xpub == xpub_entry['xpub'] and
                        xpub_result.derivation_path == xpub_entry['derivation_path']
                    )
                    if found:
                        addresses_dict = xpub_entry['addresses']
                        break

                if addresses_dict is None:  # new xpub, create the mapping
                    new_entry: Dict[str, Any] = {
                        'xpub': xpub_result.xpub.xpub,
                        'derivation_path': xpub_result.derivation_path,
                        'addresses': {},
                    }
                    btc_balances['xpubs'].append(new_entry)
                    addresses_dict = new_entry['addresses']

            addresses_dict[btc_account] = balances.serialize()

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
    totals: BalanceSheet

    def serialize(self) -> Dict[str, Dict]:
        return {
            'per_account': self.per_account.serialize(),
            'totals': self.totals.serialize(),
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
            data_directory: Path,
            beaconchain: 'BeaconChain',
            eth_modules: Optional[List[str]] = None,
    ):
        log.debug('Initializing ChainManager')
        super().__init__()
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.accounts = blockchain_accounts
        self.data_directory = data_directory
        self.beaconchain = beaconchain

        self.defi_balances_last_query_ts = Timestamp(0)
        self.defi_balances: Dict[ChecksumEthAddress, List[DefiProtocolBalances]] = {}
        self.defi_lock = Semaphore()
        self.eth2_lock = Semaphore()

        # Per account balances
        self.balances = BlockchainBalances(db=database)
        # Per asset total balances
        self.totals: BalanceSheet = BalanceSheet()
        # TODO: Perhaps turn this mapping into a typed dict?
        self.eth_modules: Dict[str, Union[EthereumModule, Literal['loading']]] = {}
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
                elif given_module == 'compound':
                    self.eth_modules['compound'] = 'loading'
                    # Since Compound initialization needs a few network calls we do it async
                    greenlet_manager.spawn_and_track(
                        after_seconds=None,
                        task_name='Initialize Compound object',
                        method=self._initialize_compound,
                        premium=premium,
                    )
                elif given_module == 'uniswap':
                    self.eth_modules['uniswap'] = Uniswap(
                        ethereum_manager=ethereum_manager,
                        database=self.database,
                        premium=premium,
                        msg_aggregator=msg_aggregator,
                        data_directory=self.data_directory,
                    )
                elif given_module == 'yearn_vaults':
                    self.eth_modules['yearn_vaults'] = YearnVaults(
                        ethereum_manager=ethereum_manager,
                        database=self.database,
                        premium=premium,
                        msg_aggregator=msg_aggregator,
                    )
                else:
                    log.error(f'Unrecognized module value {given_module} given. Skipping...')

        self.premium = premium
        self.greenlet_manager = greenlet_manager
        self.zerion = Zerion(ethereum_manager=self.ethereum, msg_aggregator=self.msg_aggregator)

        for name, module in self.iterate_modules():
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=f'startup of {name}',
                method=module.on_startup,
            )

    def _initialize_compound(self, premium: Optional[Premium]) -> None:
        self.eth_modules['compound'] = Compound(
            ethereum_manager=self.ethereum,
            database=self.database,
            premium=premium,
            msg_aggregator=self.msg_aggregator,
        )

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

    def iterate_modules(self) -> Iterator[Tuple[str, EthereumModule]]:
        for name, module in self.eth_modules.items():
            if module == 'loading':
                continue

            yield name, module

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

    @property
    def compound(self) -> Optional[Compound]:
        module = self.eth_modules.get('compound', None)
        if not module:
            return None

        if module == 'loading':
            # Keep trying out with a timeout of 10 seconds unitl initialization finishes
            with gevent.Timeout(10):
                while True:
                    module = self.eth_modules.get('compound', None)
                    if module == 'loading':
                        gevent.sleep(0.5)
                    else:
                        return module  # type: ignore
        return module  # type: ignore

    @property
    def uniswap(self) -> Optional[Uniswap]:
        module = self.eth_modules.get('uniswap', None)
        if not module:
            return None

        return module  # type: ignore

    @property
    def yearn_vaults(self) -> Optional[YearnVaults]:
        module = self.eth_modules.get('yearn_vaults', None)
        if not module:
            return None

        return module  # type: ignore

    def queried_addresses_for_module(self, module: ModuleName) -> List[ChecksumEthAddress]:
        """Returns the addresses to query for the given module/protocol"""
        result = QueriedAddresses(self.database).get_queried_addresses_for_module(module)
        return result if result is not None else self.accounts.eth

    def get_balances_update(self) -> BlockchainBalancesUpdate:
        return BlockchainBalancesUpdate(per_account=self.balances, totals=self.totals)

    @protect_with_lock(arguments_matter=True)
    @cache_response_timewise()
    def query_balances(
            self,  # pylint: disable=unused-argument
            blockchain: Optional[SupportedBlockchain] = None,
            force_token_detection: bool = False,
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> BlockchainBalancesUpdate:
        """Queries either all, or specific blockchain balances

        If force detection is true, then the ethereum token detection is forced.

        May raise:
        - RemoteError if an external service such as Etherscan or blockchain.info
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        should_query_eth = not blockchain or blockchain == SupportedBlockchain.ETHEREUM
        should_query_btc = not blockchain or blockchain == SupportedBlockchain.BITCOIN

        if should_query_eth:
            self.query_ethereum_balances(force_token_detection=force_token_detection)
        if should_query_btc:
            self.query_btc_balances()

        return self.get_balances_update()

    @protect_with_lock()
    @cache_response_timewise()
    def query_btc_balances(self) -> None:
        """Queries blockchain.info/blockstream for the balance of all BTC accounts

        May raise:
        - RemotError if there is a problem querying any remote
        """
        if len(self.accounts.btc) == 0:
            return

        self.balances.btc = {}
        btc_usd_price = Inquirer().find_usd_price(A_BTC)
        total = FVal(0)
        balances = get_bitcoin_addresses_balances(self.accounts.btc)
        for account, balance in balances.items():
            total += balance
            self.balances.btc[account] = Balance(
                amount=balance,
                usd_value=balance * btc_usd_price,
            )
        self.totals.assets[A_BTC] = Balance(amount=total, usd_value=total * btc_usd_price)

    def sync_btc_accounts_with_db(self) -> None:
        """Call this function after having deleted BTC accounts from the DB to
        sync the chain manager's balances and accounts with the DB

        For example this is called after removing an xpub which deletes all derived
        addresses from the DB.
        """
        db_btc_accounts = self.database.get_blockchain_accounts().btc
        accounts_to_remove = []
        for btc_account in self.accounts.btc:
            if btc_account not in db_btc_accounts:
                accounts_to_remove.append(btc_account)

        balances_mapping = get_bitcoin_addresses_balances(accounts_to_remove)
        balances = [balances_mapping.get(x, ZERO) for x in accounts_to_remove]
        self.modify_blockchain_accounts(
            blockchain=SupportedBlockchain.BITCOIN,
            accounts=accounts_to_remove,
            append_or_remove='remove',
            add_or_sub=operator.sub,
            already_queried_balances=balances,
        )

    def modify_btc_account(
            self,
            account: BTCAddress,
            append_or_remove: str,
            add_or_sub: AddOrSub,
            already_queried_balance: Optional[FVal] = None,
    ) -> None:
        """Either appends or removes a BTC acccount.

        If already_queried_balance is not None then instead of querying the balance
        of the account we can use the already queried one.

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
            if already_queried_balance is None:
                balances = get_bitcoin_addresses_balances([account])
                balance = balances[account]
            else:
                balance = already_queried_balance
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
            self.totals.assets[A_BTC] = Balance()
        else:
            self.totals.assets[A_BTC] = add_or_sub(
                self.totals.assets[A_BTC],
                Balance(balance, usd_balance),
            )

        # At the very end add/remove it from the accounts
        getattr(self.accounts.btc, append_or_remove)(account)

    def modify_eth_account(
            self,
            account: ChecksumEthAddress,
            append_or_remove: str,
    ) -> None:
        """Either appends or removes an ETH acccount.

        Call with 'append' to add the account
        Call with 'remove' remove the account

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
            self.balances.eth[account] = BalanceSheet(
                assets=defaultdict(Balance, {A_ETH: Balance(amount, usd_value)}),
            )
            # Check if the new account has any staked eth2 deposits
            self.account_for_staked_eth2_balances([account], at_addition=True)
        elif append_or_remove == 'remove':
            if account not in self.accounts.eth:
                raise InputError('Tried to remove a non existing ETH account')
            self.accounts.eth.remove(account)
            balances = self.balances.eth.get(account, None)
            if balances is not None:
                for asset, balance in balances.assets.items():
                    self.totals.assets[asset] -= balance
                    if self.totals.assets[asset].amount <= ZERO:
                        self.totals.assets[asset] = Balance()
            self.balances.eth.pop(account, None)
        else:
            raise AssertionError('Programmer error: Should be append or remove')

        if len(self.balances.eth) == 0:
            # If the last account was removed balance should be 0
            self.totals.assets[A_ETH] = Balance()
        elif append_or_remove == 'append':
            self.totals.assets[A_ETH] += Balance(amount, usd_value)
            self._query_ethereum_tokens(
                action=AccountAction.APPEND,
                given_accounts=[account],
            )

    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
            already_queried_balances: Optional[List[FVal]] = None,
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
            self.flush_cache('query_balances', arguments_matter=True, blockchain=blockchain, ignore_cache=True)  # noqa: E501

        result = self.modify_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
            append_or_remove='append',
            add_or_sub=operator.add,
            already_queried_balances=already_queried_balances,
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
            add_or_sub: AddOrSub,
            already_queried_balances: Optional[List[FVal]] = None,
    ) -> BlockchainBalancesUpdate:
        """Add or remove a list of blockchain account

        May raise:

        - InputError if accounts to remove do not exist.
        - EthSyncError if there is a problem querying the ethereum chain
        - RemoteError if there is a problem querying an external service such
          as etherscan or blockchain.info
        """
        if blockchain == SupportedBlockchain.BITCOIN:
            # we are adding/removing accounts, make sure query cache is flushed
            self.flush_cache('query_btc_balances', arguments_matter=True)
            self.flush_cache('query_balances', arguments_matter=True)
            self.flush_cache('query_balances', arguments_matter=True, blockchain=SupportedBlockchain.BITCOIN)  # noqa: E501
            for idx, account in enumerate(accounts):
                a_balance = already_queried_balances[idx] if already_queried_balances else None
                self.modify_btc_account(
                    BTCAddress(account),
                    append_or_remove,
                    add_or_sub,
                    already_queried_balance=a_balance,
                )

        elif blockchain == SupportedBlockchain.ETHEREUM:
            # we are adding/removing accounts, make sure query cache is flushed
            self.flush_cache('query_ethereum_balances', arguments_matter=True, force_token_detection=False)  # noqa: E501
            self.flush_cache('query_ethereum_balances', arguments_matter=True, force_token_detection=True)  # noqa: E501
            self.flush_cache('query_balances', arguments_matter=True)
            self.flush_cache('query_balances', arguments_matter=True, blockchain=SupportedBlockchain.ETHEREUM)  # noqa: E501
            for account in accounts:
                address = deserialize_ethereum_address(account)
                try:
                    self.modify_eth_account(
                        account=address,
                        append_or_remove=append_or_remove,
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

                # Also modify and take into account defi balances
                if append_or_remove == 'append':
                    balances = self.zerion.all_balances_for_account(address)
                    if len(balances) != 0:
                        self.defi_balances[address] = balances
                        self._add_account_defi_balances_to_token_and_totals(
                            account=address,
                            balances=balances,
                        )
                else:  # remove
                    self.defi_balances.pop(address, None)
                # For each module run the corresponding callback for the address
                for _, module in self.iterate_modules():
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
            force_detection: bool = False,
    ) -> None:
        """Queries ethereum token balance via either etherscan or ethereum node

        By default queries all accounts but can also be given a specific list of
        accounts to query.

        Should come here during addition of a new account or querying of all token
        balances.

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
            balance_result, token_usd_price = ethtokens.query_tokens_for_addresses(
                addresses=accounts,
                force_detection=force_detection,
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

        # Update the per account token balance and usd value
        token_totals: Dict[EthereumToken, FVal] = defaultdict(FVal)
        eth_balances = self.balances.eth
        for account, token_balances in balance_result.items():
            for token, token_balance in token_balances.items():
                if token_usd_price[token] == ZERO:
                    # skip tokens that have no price
                    continue

                token_totals[token] += token_balance
                usd_value = token_balance * token_usd_price[token]
                eth_balances[account].assets[token] = Balance(
                    amount=token_balance,
                    usd_value=usd_value,
                )

        # Update the totals
        for token, token_total_balance in token_totals.items():
            if action == AccountAction.QUERY:
                self.totals.assets[token] = Balance(
                    amount=token_total_balance,
                    usd_value=token_total_balance * token_usd_price[token],
                )
            else:  # addition
                self.totals.assets[token] += Balance(
                    amount=token_total_balance,
                    usd_value=token_total_balance * token_usd_price[token],
                )

    def query_ethereum_tokens(self, force_detection: bool) -> None:
        """Queries the ethereum token balances and populates the state

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        # Clear out all previous token balances
        for token in [x for x, _ in self.totals.assets.items() if x.is_eth_token()]:
            del self.totals.assets[token]
        for token in [x for x, _ in self.totals.liabilities.items() if x.is_eth_token()]:
            del self.totals.liabilities[token]

        self._query_ethereum_tokens(action=AccountAction.QUERY, force_detection=force_detection)

    def query_defi_balances(self) -> Dict[ChecksumEthAddress, List[DefiProtocolBalances]]:
        """Queries DeFi balances from Zerion contract and updates the state

        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        with self.defi_lock:
            if ts_now() - self.defi_balances_last_query_ts < DEFI_BALANCES_REQUERY_SECONDS:
                return self.defi_balances

            # query zerion for defi balances
            self.defi_balances = {}
            for account in self.accounts.eth:
                balances = self.zerion.all_balances_for_account(account)
                if len(balances) != 0:
                    self.defi_balances[account] = balances

            self.defi_balances_last_query_ts = ts_now()
            return self.defi_balances

    @protect_with_lock()
    @cache_response_timewise()
    def query_ethereum_balances(self, force_token_detection: bool) -> None:
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
            self.balances.eth[account] = BalanceSheet(
                assets=defaultdict(Balance, {A_ETH: Balance(balance, usd_value)}),
            )
        self.totals.assets[A_ETH] = Balance(amount=eth_total, usd_value=eth_total * eth_usd_price)

        self.query_defi_balances()
        self.query_ethereum_tokens(force_token_detection)
        self._add_protocol_balances()

    def _add_protocol_balances(self) -> None:
        """Also count token balances that may come from various protocols"""
        # If we have anything in DSR also count it towards total blockchain balances
        eth_balances = self.balances.eth
        dsr_module = self.makerdao_dsr
        if dsr_module is not None:
            additional_total = Balance()
            current_dsr_report = dsr_module.get_current_dsr()
            for dsr_account, balance_entry in current_dsr_report.balances.items():

                if balance_entry.amount == ZERO:
                    continue

                eth_balances[dsr_account].assets[A_DAI] += balance_entry
                additional_total += balance_entry

            if additional_total.amount != ZERO:
                self.totals.assets[A_DAI] += additional_total

        # Also count the vault balance and add it to the totals
        vaults_module = self.makerdao_vaults
        if vaults_module is not None:
            balances = vaults_module.get_balances()
            for address, entry in balances.items():
                if address not in eth_balances:
                    self.msg_aggregator.add_error(
                        f'The owner of a vault {address} was not in the tracked addresses.'
                        f' This should not happen and is probably a bug. Please report it.',
                    )
                else:
                    eth_balances[address] += entry
                    self.totals += entry

        # Count ETH staked in Eth2 beacon chain
        self.account_for_staked_eth2_balances(addresses=self.accounts.eth, at_addition=False)
        # Finally count the balances detected in various protocols in defi balances
        self.add_defi_balances_to_token_and_totals()

    def _add_account_defi_balances_to_token_and_totals(
            self,
            account: ChecksumEthAddress,
            balances: List[DefiProtocolBalances],
    ) -> None:
        """Add a single account's defi balances to per account and totals"""
        for entry in balances:

            skip_list = DEFI_PROTOCOLS_TO_SKIP_ASSETS.get(entry.protocol.name, None)
            double_entry = (
                entry.balance_type == 'Asset' and
                skip_list and
                (skip_list is True or entry.base_balance.token_symbol in skip_list)  # type: ignore
            )

            # We have to filter out specific balances/protocols here to not get double entries
            if double_entry:
                continue

            if entry.balance_type == 'Asset' and entry.base_balance.token_symbol == 'ETH':
                # If ETH appears as asset here I am not sure how to handle, so ignore for now
                log.warning(
                    f'Found ETH in DeFi balances for account: {account} and '
                    f'protocol: {entry.protocol.name}. Ignoring ...',
                )
                continue

            try:
                asset = Asset(entry.base_balance.token_symbol)
            except UnknownAsset:
                log.warning(
                    f'Found unknown asset {entry.base_balance.token_symbol} in DeFi '
                    f'balances for account: {account} and '
                    f'protocol: {entry.protocol.name}. Ignoring ...',
                )
                continue

            token = EthereumToken.from_asset(asset)
            if token is not None and token.ethereum_address != entry.base_balance.token_address:
                log.warning(
                    f'Found token {token.identifier} with address '
                    f'{entry.base_balance.token_address} instead of expected '
                    f'{token.ethereum_address} for account: {account} and '
                    f'protocol: {entry.protocol.name}. Ignoring ...',
                )
                continue

            eth_balances = self.balances.eth
            if entry.balance_type == 'Asset':
                eth_balances[account].assets[asset] += entry.base_balance.balance
                self.totals.assets[asset] += entry.base_balance.balance
            elif entry.balance_type == 'Debt':
                eth_balances[account].liabilities[asset] += entry.base_balance.balance
                self.totals.liabilities[asset] += entry.base_balance.balance
            else:
                log.warning(  # type: ignore # is an unreachable statement but we are defensive
                    f'Zerion Defi Adapter returned unknown asset type {entry.balance_type}. '
                    f'Skipping ...',
                )
                continue

    def add_defi_balances_to_token_and_totals(self) -> None:
        """Take into account defi balances and add them to per account and totals"""
        for account, defi_balances in self.defi_balances.items():
            self._add_account_defi_balances_to_token_and_totals(
                account=account,
                balances=defi_balances,
            )

    def account_for_staked_eth2_balances(
            self,
            addresses: List[ChecksumEthAddress],
            at_addition: bool = False,
    ) -> None:
        if not at_addition:
            # Before querying the new balances, delete the ones in memory if any
            self.totals.assets.pop(A_ETH2, None)
            for _, entry in self.balances.eth.items():
                if A_ETH2 in entry.assets:
                    del entry.assets[A_ETH2]

        mapping = get_eth2_balances(self.beaconchain, addresses)
        for address, balance in mapping.items():
            self.balances.eth[address].assets[A_ETH2] = balance
            self.totals.assets[A_ETH2] += balance

    def get_eth2_staking_details(self) -> Dict[str, Any]:
        with self.eth2_lock:
            deposits = get_eth2_staking_deposits(
                ethereum=self.ethereum,
                addresses=self.accounts.eth,
                has_premium=self.premium is not None,
                msg_aggregator=self.msg_aggregator,
                database=self.database,
            )

        current_usd_price = Inquirer().find_usd_price(A_ETH)
        details = get_eth2_balances_via_deposits(beaconchain=self.beaconchain, deposits=deposits)
        return {
            'deposits': [x._asdict() for x in deposits],
            'details': [x.serialize(current_usd_price) for x in details],
        }
