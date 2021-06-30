import logging
import operator
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from importlib import import_module
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
    overload,
)

from gevent.lock import Semaphore
from typing_extensions import Literal
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.accounting.structures import (
    AssetBalance,
    Balance,
    BalanceSheet,
    DefiEvent,
    DefiEventType,
)
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.bitcoin import get_bitcoin_addresses_balances
from rotkehlchen.chain.ethereum.defi.chad import DefiChad
from rotkehlchen.chain.ethereum.defi.structures import DefiProtocolBalances
from rotkehlchen.chain.ethereum.modules import (
    Aave,
    Adex,
    Balancer,
    Compound,
    Eth2,
    Loopring,
    MakerdaoDsr,
    MakerdaoVaults,
    Uniswap,
    YearnVaults,
    YearnVaultsV2,
)
from rotkehlchen.chain.ethereum.tokens import EthTokens
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.chain.substrate.manager import wait_until_a_node_is_available
from rotkehlchen.chain.substrate.typing import KusamaAddress
from rotkehlchen.chain.substrate.utils import KUSAMA_NODE_CONNECTION_TIMEOUT
from rotkehlchen.constants.assets import A_ADX, A_BTC, A_DAI, A_ETH, A_ETH2, A_KSM
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.errors import (
    EthSyncError,
    InputError,
    ModuleInactive,
    ModuleInitializationFailure,
    RemoteError,
    UnknownAsset,
)
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import (
    BTCAddress,
    ChecksumEthAddress,
    ListOfBlockchainAddresses,
    ModuleName,
    Price,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn, cache_response_timewise
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.typing import Eth2Deposit, ValidatorDetails
    from rotkehlchen.chain.substrate.manager import SubstrateManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.beaconchain import BeaconChain

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _module_name_to_class(module_name: ModuleName) -> EthereumModule:
    class_name = ''.join(word.title() for word in module_name.split('_'))
    try:
        etherem_modules_module = import_module('rotkehlchen.chain.ethereum.modules')
    except ModuleNotFoundError as e:
        # This should never happen
        raise AssertionError('Could not load ethereum modules') from e
    module = getattr(etherem_modules_module, class_name, None)
    assert module, f'Could not find object {class_name} in ethereum modules'
    return module


DEFI_BALANCES_REQUERY_SECONDS = 600

# Mapping to token symbols to ignore. True means all
DEFI_PROTOCOLS_TO_SKIP_ASSETS = {
    # aTokens are already detected at token balance queries
    'Aave': True,  # True means all
    'Aave V2': True,  # True means all
    # cTokens are already detected at token balance queries
    'Compound': True,  # True means all
    # Curve balances are detected by our scan for ERC20 tokens
    'Curve': True,  # True means all
    # Chitoken is in our all_assets.json
    'Chi Gastoken by 1inch': True,  # True means all
    # yearn vault balances are detected by the yTokens
    'yearn.finance • Vaults': True,  # True means all
    'Yearn Token Vaults': True,
    # Synthetix SNX token is in all_assets.json
    'Synthetix': ['SNX'],
    # Ampleforth's AMPL token is in all_assets.json
    'Ampleforth': ['AMPL'],
    # MakerDao vault balances are already detected by our code.
    # Note that DeFi SDK only detects them for the proxies.
    'Multi-Collateral Dai': True,  # True means all
    # We already got some pie dao tokens in all_assets.json
    'PieDAO': ['BCP', 'BTC++', 'DEFI++', 'DEFI+S', 'DEFI+L', 'YPIE'],
}


T = TypeVar('T')
AddOrSub = Callable[[T, T], T]


class AccountAction(Enum):
    QUERY = 1
    APPEND = 2
    REMOVE = 3
    DSR_PROXY_APPEND = 4


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BlockchainBalances:
    db: 'DBHandler'  # Need this to serialize BTC accounts with xpub mappings
    eth: DefaultDict[ChecksumEthAddress, BalanceSheet] = field(init=False)
    btc: Dict[BTCAddress, Balance] = field(init=False)
    ksm: Dict[KusamaAddress, BalanceSheet] = field(init=False)

    def copy(self) -> 'BlockchainBalances':
        balances = BlockchainBalances(db=self.db)
        balances.eth = self.eth.copy()
        balances.btc = self.btc.copy()
        balances.ksm = self.ksm.copy()
        return balances

    def __post_init__(self) -> None:
        self.eth = defaultdict(BalanceSheet)
        self.btc = defaultdict(Balance)
        self.ksm = defaultdict(BalanceSheet)

    def serialize(self) -> Dict[str, Dict]:
        eth_balances = {k: v.serialize() for k, v in self.eth.items()}
        btc_balances: Dict[str, Any] = {}
        ksm_balances = {k: v.serialize() for k, v in self.ksm.items()}
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
        if ksm_balances != {}:
            blockchain_balances['KSM'] = ksm_balances
        return blockchain_balances

    def is_queried(self, blockchain: SupportedBlockchain) -> bool:
        if blockchain == SupportedBlockchain.ETHEREUM:
            return self.eth != {}
        if blockchain == SupportedBlockchain.BITCOIN:
            return self.btc != {}
        if blockchain == SupportedBlockchain.KUSAMA:
            return self.ksm != {}
        # else
        raise AssertionError('Invalid blockchain value')

    def account_exists(
            self,
            blockchain: SupportedBlockchain,
            account: Union[BTCAddress, ChecksumEthAddress, KusamaAddress],
    ) -> bool:
        if blockchain == SupportedBlockchain.ETHEREUM:
            return account in self.eth
        if blockchain == SupportedBlockchain.BITCOIN:
            return account in self.btc
        if blockchain == SupportedBlockchain.KUSAMA:
            return account in self.ksm
        # else
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


class ChainManager(CacheableMixIn, LockableQueryMixIn):

    def __init__(
            self,
            blockchain_accounts: BlockchainAccounts,
            ethereum_manager: 'EthereumManager',
            kusama_manager: 'SubstrateManager',
            msg_aggregator: MessagesAggregator,
            database: 'DBHandler',
            greenlet_manager: GreenletManager,
            premium: Optional[Premium],
            data_directory: Path,
            beaconchain: 'BeaconChain',
            btc_derivation_gap_limit: int,
            eth_modules: Optional[List[ModuleName]] = None,
    ):
        log.debug('Initializing ChainManager')
        super().__init__()
        self.ethereum = ethereum_manager
        self.kusama = kusama_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.accounts = blockchain_accounts
        self.data_directory = data_directory
        self.beaconchain = beaconchain
        self.btc_derivation_gap_limit = btc_derivation_gap_limit
        self.defi_balances_last_query_ts = Timestamp(0)
        self.defi_balances: Dict[ChecksumEthAddress, List[DefiProtocolBalances]] = {}

        self.eth2_details: List['ValidatorDetails'] = []

        self.defi_lock = Semaphore()
        self.btc_lock = Semaphore()
        self.eth_lock = Semaphore()
        self.ksm_lock = Semaphore()

        # Per account balances
        self.balances = BlockchainBalances(db=database)
        # Per asset total balances
        self.totals: BalanceSheet = BalanceSheet()
        self.premium = premium
        self.greenlet_manager = greenlet_manager
        # TODO: Turn this mapping into a typed dict once we upgrade to python 3.8
        self.eth_modules: Dict[ModuleName, Union[EthereumModule]] = {}
        if eth_modules:
            for given_module in eth_modules:
                self.activate_module(given_module)

        self.defichad = DefiChad(
            ethereum_manager=self.ethereum,
            msg_aggregator=self.msg_aggregator,
        )

    def __del__(self) -> None:
        del self.ethereum

    def set_eth_rpc_endpoint(self, endpoint: str) -> Tuple[bool, str]:
        return self.ethereum.set_rpc_endpoint(endpoint)

    def set_ksm_rpc_endpoint(self, endpoint: str) -> Tuple[bool, str]:
        return self.kusama.set_rpc_endpoint(endpoint)

    def deactivate_premium_status(self) -> None:
        for _, module in self.iterate_modules():
            if getattr(module, 'premium', None):
                module.premium = None  # type: ignore

    def process_new_modules_list(self, module_names: List[ModuleName]) -> None:
        """Processes a new list of active modules

        Adds those missing, and removes those not present
        """
        existing_names = set(self.eth_modules.keys())
        given_modules_set = set(module_names)
        modules_to_remove = existing_names.difference(given_modules_set)
        modules_to_add = given_modules_set.difference(existing_names)

        for name in modules_to_remove:
            self.deactivate_module(name)
        for name in modules_to_add:
            self.activate_module(name)

    def iterate_modules(self) -> Iterator[Tuple[str, EthereumModule]]:
        for name, module in self.eth_modules.items():
            yield name, module

    def queried_addresses_for_module(self, module: ModuleName) -> List[ChecksumEthAddress]:
        """Returns the addresses to query for the given module/protocol"""
        result = QueriedAddresses(self.database).get_queried_addresses_for_module(module)
        return result if result is not None else self.accounts.eth

    def activate_module(self, module_name: ModuleName) -> Optional[EthereumModule]:
        """Activates an ethereum module by module name"""
        module = self.eth_modules.get(module_name, None)
        if module:
            return module  # already activated

        logger.debug(f'Activating {module_name} module')
        kwargs = {}
        if module_name == 'eth2':
            kwargs['beaconchain'] = self.beaconchain
        klass = _module_name_to_class(module_name)
        # TODO: figure out the type here: class EthereumModule not callable.
        try:
            instance = klass(  # type: ignore
                ethereum_manager=self.ethereum,
                database=self.database,
                premium=self.premium,
                msg_aggregator=self.msg_aggregator,
                **kwargs,
            )
        except ModuleInitializationFailure as e:
            logger.error(f'Failed to activate {module_name} due to: {str(e)}')
            return None

        self.eth_modules[module_name] = instance
        # also run any startup initialization actions for the module
        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=f'startup of {module_name}',
            exception_is_error=True,
            method=instance.on_startup,
        )
        return instance

    def deactivate_module(self, module_name: ModuleName) -> None:
        """Deactivates an ethereum module by name"""
        instance = self.eth_modules.pop(module_name, None)
        if instance is None:
            return  # nothing to do

        logger.debug(f'Deactivating {module_name} module')
        instance.deactivate()
        del instance
        return

    @overload
    def get_module(self, module_name: Literal['aave']) -> Optional[Aave]:
        ...

    @overload
    def get_module(self, module_name: Literal['adex']) -> Optional[Adex]:
        ...

    @overload
    def get_module(self, module_name: Literal['balancer']) -> Optional[Balancer]:
        ...

    @overload
    def get_module(self, module_name: Literal['compound']) -> Optional[Compound]:
        ...

    @overload
    def get_module(self, module_name: Literal['eth2']) -> Optional[Eth2]:
        ...

    @overload
    def get_module(self, module_name: Literal['loopring']) -> Optional[Loopring]:
        ...

    @overload
    def get_module(self, module_name: Literal['makerdao_dsr']) -> Optional[MakerdaoDsr]:
        ...

    @overload
    def get_module(self, module_name: Literal['makerdao_vaults']) -> Optional[MakerdaoVaults]:
        ...

    @overload
    def get_module(self, module_name: Literal['uniswap']) -> Optional[Uniswap]:
        ...

    @overload
    def get_module(self, module_name: Literal['yearn_vaults']) -> Optional[YearnVaults]:
        ...

    @overload
    def get_module(self, module_name: Literal['yearn_vaults_v2']) -> Optional[YearnVaultsV2]:
        ...

    def get_module(self, module_name: ModuleName) -> Optional[Any]:
        instance = self.eth_modules.get(module_name, None)
        if instance is None:  # not activated
            return None

        return instance

    def get_balances_update(self) -> BlockchainBalancesUpdate:
        return BlockchainBalancesUpdate(
            per_account=self.balances.copy(),
            totals=self.totals.copy(),
        )

    def check_accounts_exist(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> None:
        """Checks if any of the accounts already exist and if they do raises an input error"""
        existing_accounts = []
        for account in accounts:
            if self.balances.account_exists(blockchain, account):
                existing_accounts.append(account)

        if len(existing_accounts) != 0:
            raise InputError(
                f'Blockchain account/s {",".join(existing_accounts)} already exist',
            )

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
        should_query_ksm = not blockchain or blockchain == SupportedBlockchain.KUSAMA

        if should_query_eth:
            self.query_ethereum_balances(force_token_detection=force_token_detection)
        if should_query_btc:
            self.query_btc_balances()
        if should_query_ksm:
            self.query_kusama_balances()

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

    @protect_with_lock()
    @cache_response_timewise()
    def query_kusama_balances(self, wait_available_node: bool = True) -> None:
        """Queries the KSM balances of the accounts via Kusama endpoints.

        May raise:
        - RemotError: if no nodes are available or the balances request fails.
        """
        if len(self.accounts.ksm) == 0:
            return

        ksm_usd_price = Inquirer().find_usd_price(A_KSM)
        if wait_available_node:
            wait_until_a_node_is_available(
                substrate_manager=self.kusama,
                seconds=KUSAMA_NODE_CONNECTION_TIMEOUT,
            )

        account_amount = self.kusama.get_accounts_balance(self.accounts.ksm)
        total_balance = Balance()
        for account, amount in account_amount.items():
            balance = Balance(
                amount=amount,
                usd_value=amount * ksm_usd_price,
            )
            self.balances.ksm[account] = BalanceSheet(
                assets=defaultdict(Balance, {A_KSM: balance}),
            )
            total_balance += balance
        self.totals.assets[A_KSM] = total_balance

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

                for asset, balance in balances.liabilities.items():
                    self.totals.liabilities[asset] -= balance
                    if self.totals.liabilities[asset].amount <= ZERO:
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

    def modify_kusama_account(
            self,
            account: KusamaAddress,
            append_or_remove: Literal['append', 'remove'],
    ) -> None:
        """Either appends or removes a kusama acccount.

        Call with 'append' to add the account
        Call with 'remove' remove the account

        May raise:
        - Input error if the given_account is not a valid kusama address
        - RemoteError if there is a problem with a query to an external
        service such as Kusama nodes or cryptocompare
        """
        if append_or_remove not in ('append', 'remove'):
            raise AssertionError(f'Unexpected action: {append_or_remove}')
        if append_or_remove == 'remove' and account not in self.accounts.ksm:
            raise InputError('Tried to remove a non existing KSM account')

        ksm_usd_price = Inquirer().find_usd_price(A_KSM)
        if append_or_remove == 'append':
            # Wait until a node is connected when adding a KSM address for the
            # first time.
            if len(self.kusama.available_nodes_call_order) == 0:
                self.kusama.attempt_connections()
                wait_until_a_node_is_available(
                    substrate_manager=self.kusama,
                    seconds=KUSAMA_NODE_CONNECTION_TIMEOUT,
                )
            amount = self.kusama.get_account_balance(account)
            balance = Balance(amount=amount, usd_value=amount * ksm_usd_price)
            self.accounts.ksm.append(account)
            self.balances.ksm[account] = BalanceSheet(
                assets=defaultdict(Balance, {A_KSM: balance}),
            )
            self.totals.assets[A_KSM] += balance
        if append_or_remove == 'remove':
            if len(self.balances.ksm) > 1:
                if account in self.balances.ksm:
                    self.totals.assets[A_KSM] -= self.balances.ksm[account].assets[A_KSM]
            else:  # If the last account was removed balance should be 0
                self.totals.assets[A_KSM] = Balance()
            self.balances.ksm.pop(account, None)
            self.accounts.ksm.remove(account)

    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
            already_queried_balances: Optional[List[FVal]] = None,
    ) -> BlockchainBalancesUpdate:
        """Adds new blockchain accounts and requeries all balances after the addition.
        The accounts are added in the blockchain object and not in the database.
        Returns the new total balances, the actually added accounts (some
        accounts may have been invalid) and also any errors that occurred
        during the addition.

        May Raise:
        - EthSyncError from modify_blockchain_accounts
        - InputError if the given accounts list is empty, or if it contains invalid accounts,
          or if any account already exists.
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
            append_or_remove: Literal['append', 'remove'],
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
            with self.btc_lock:
                if append_or_remove == 'append':
                    self.check_accounts_exist(blockchain, accounts)

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
            with self.eth_lock:
                if append_or_remove == 'append':
                    self.check_accounts_exist(blockchain, accounts)

                # we are adding/removing accounts, make sure query cache is flushed
                self.flush_cache('query_ethereum_balances', arguments_matter=True, force_token_detection=False)  # noqa: E501
                self.flush_cache('query_ethereum_balances', arguments_matter=True, force_token_detection=True)  # noqa: E501
                self.flush_cache('query_balances', arguments_matter=True)
                self.flush_cache('query_balances', arguments_matter=True, blockchain=SupportedBlockchain.ETHEREUM)  # noqa: E501
                for account in accounts:
                    # when the API adds or removes an address, the deserialize function at
                    # EthereumAddressField is called, so we expect from the addresses retrieved by
                    # this function to be already checksumed.
                    address = string_to_ethereum_address(account)
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
                        ) from e

                    # Also modify and take into account defi balances
                    if append_or_remove == 'append':
                        balances = self.defichad.query_defi_balances([address])
                        address_balances = balances.get(address, [])
                        if len(address_balances) != 0:
                            self.defi_balances[address] = address_balances
                            self._add_account_defi_balances_to_token_and_totals(
                                account=address,
                                balances=address_balances,
                            )
                    else:  # remove
                        self.defi_balances.pop(address, None)
                    # For each module run the corresponding callback for the address
                    for _, module in self.iterate_modules():
                        if append_or_remove == 'append':
                            new_module_balances = module.on_account_addition(address)
                            if new_module_balances:
                                for entry in new_module_balances:
                                    self.balances.eth[address].assets[entry.asset] += entry.balance
                                    self.totals.assets[entry.asset] += entry.balance
                        else:  # remove
                            module.on_account_removal(address)

        elif blockchain == SupportedBlockchain.KUSAMA:
            with self.ksm_lock:
                if append_or_remove == 'append':
                    self.check_accounts_exist(blockchain, accounts)

                # we are adding/removing accounts, make sure query cache is flushed
                self.flush_cache('query_kusama_balances', arguments_matter=True)
                self.flush_cache('query_balances', arguments_matter=True)
                self.flush_cache('query_balances', arguments_matter=True, blockchain=SupportedBlockchain.KUSAMA)  # noqa: E501
                for account in accounts:
                    self.modify_kusama_account(
                        account=KusamaAddress(account),
                        append_or_remove=append_or_remove,
                    )
        else:
            # That should not happen. Should be checked by marshmallow
            raise AssertionError(
                'Unsupported blockchain {} provided at remove_blockchain_account'.format(
                    blockchain),
            )

        return self.get_balances_update()

    def _update_balances_after_token_query(
            self,
            action: AccountAction,
            balance_result: Dict[ChecksumEthAddress, Dict[EthereumToken, FVal]],
            token_usd_price: Dict[EthereumToken, Price],
    ) -> None:
        token_totals: Dict[EthereumToken, FVal] = defaultdict(FVal)
        # Update the per account token balance and usd value
        eth_balances = self.balances.eth
        for account, token_balances in balance_result.items():
            for token, token_balance in token_balances.items():
                if token_usd_price[token] == ZERO:
                    # skip tokens that have no price
                    continue

                token_totals[token] += token_balance
                balance = Balance(
                    amount=token_balance,
                    usd_value=token_balance * token_usd_price[token],
                )
                if action == AccountAction.DSR_PROXY_APPEND:
                    eth_balances[account].assets[token] += balance
                else:
                    eth_balances[account].assets[token] = balance

        # Update the totals
        for token, token_total_balance in token_totals.items():
            balance = Balance(
                amount=token_total_balance,
                usd_value=token_total_balance * token_usd_price[token],
            )
            if action == AccountAction.QUERY:
                self.totals.assets[token] = balance
            else:  # addition
                self.totals.assets[token] += balance

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
            ) from e

        self._update_balances_after_token_query(action, balance_result, token_usd_price)  # noqa: E501

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

            # query zerion adapter contract for defi balances
            self.defi_balances = self.defichad.query_defi_balances(self.accounts.eth)
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
        dsr_module = self.get_module('makerdao_dsr')
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

        # Also count the vault balance and defi saver wallets and add it to the totals
        vaults_module = self.get_module('makerdao_vaults')
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

            proxy_mappings = vaults_module._get_accounts_having_maker_proxy()
            proxy_to_address = {}
            proxy_addresses = []
            for user_address, proxy_address in proxy_mappings.items():
                proxy_to_address[proxy_address] = user_address
                proxy_addresses.append(proxy_address)

            ethtokens = EthTokens(database=self.database, ethereum=self.ethereum)
            try:
                balance_result, token_usd_price = ethtokens.query_tokens_for_addresses(
                    addresses=proxy_addresses,
                    force_detection=False,
                )
            except BadFunctionCallOutput as e:
                log.error(
                    'Assuming unsynced chain. Got web3 BadFunctionCallOutput '
                    'exception: {}'.format(str(e)),
                )
                raise EthSyncError(
                    'Tried to use the ethereum chain of the provided client to query '
                    'token balances but the chain is not synced.',
                ) from e

            new_result = {proxy_to_address[x]: v for x, v in balance_result.items()}
            self._update_balances_after_token_query(
                action=AccountAction.DSR_PROXY_APPEND,
                balance_result=new_result,
                token_usd_price=token_usd_price,
            )

            # also query defi balances to get liabilities
            defi_balances_map = self.defichad.query_defi_balances(proxy_addresses)
            for proxy_address, defi_balances in defi_balances_map.items():
                self._add_account_defi_balances_to_token_and_totals(
                    account=proxy_to_address[proxy_address],
                    balances=defi_balances,
                )

        adex_module = self.get_module('adex')
        if adex_module is not None and self.premium is not None:
            adex_balances = adex_module.get_balances(addresses=self.queried_addresses_for_module('adex'))  # noqa: E501
            for address, balance in adex_balances.items():
                eth_balances[address].assets[A_ADX] += balance
                self.totals.assets[A_ADX] += balance

        # Count ETH staked in Eth2 beacon chain
        self.account_for_staked_eth2_balances(addresses=self.queried_addresses_for_module('eth2'))
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
                token = EthereumToken(entry.base_balance.token_address)
            except UnknownAsset:
                log.warning(
                    f'Found unknown asset {entry.base_balance.token_symbol} in DeFi '
                    f'balances for account: {account} and '
                    f'protocol: {entry.protocol.name}. Ignoring ...',
                )
                continue

            eth_balances = self.balances.eth
            if entry.balance_type == 'Asset':
                log.debug(f'Adding DeFi asset balance for {token} {entry.base_balance.balance}')
                eth_balances[account].assets[token] += entry.base_balance.balance
                self.totals.assets[token] += entry.base_balance.balance
            elif entry.balance_type == 'Debt':
                log.debug(f'Adding DeFi debt balance for {token} {entry.base_balance.balance}')
                eth_balances[account].liabilities[token] += entry.base_balance.balance
                self.totals.liabilities[token] += entry.base_balance.balance
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
    ) -> None:
        eth2 = self.get_module('eth2')
        if eth2 is None:
            return  # no eth2 module active -- do nothing

        # Before querying the new balances, delete the ones in memory if any
        self.totals.assets.pop(A_ETH2, None)
        for _, entry in self.balances.eth.items():
            if A_ETH2 in entry.assets:
                del entry.assets[A_ETH2]

        try:
            mapping = eth2.get_balances(addresses)
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Did not manage to query beaconcha.in api for addresses due to {str(e)}.'
                f' If you have Eth2 staked balances the final balance results may not be accurate',
            )
            mapping = {}
        for address, balance in mapping.items():
            self.balances.eth[address].assets[A_ETH2] = balance
            self.totals.assets[A_ETH2] += balance

    @protect_with_lock()
    @cache_response_timewise()
    def get_eth2_staking_deposits(self) -> List['Eth2Deposit']:
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive(
                'Could not query eth2 staking deposits since eth2 module is not active',
            )
        # Get the details first, to see which of the user's addresses have deposits
        details = self.get_eth2_staking_details()
        addresses = {x.eth1_depositor for x in details}
        # now narrow down the deposits query to save time
        deposits = eth2.get_staking_deposits(
            addresses=list(addresses),
            msg_aggregator=self.msg_aggregator,
            database=self.database,
        )
        return deposits

    @protect_with_lock()
    @cache_response_timewise()
    def get_eth2_staking_details(self) -> List['ValidatorDetails']:
        """May raise:
        - ModuleInactive if eth2 module is not activated
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant query eth2 staking details since eth2 module is not active')
        return eth2.get_details(addresses=self.queried_addresses_for_module('eth2'))

    @protect_with_lock()
    @cache_response_timewise()
    def get_eth2_history_events(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> List[DefiEvent]:
        """May raise:
        - ModuleInactive if eth2 module is not activated
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant query eth2 history events since eth2 module is not active')

        if to_timestamp < 1607212800:  # Dec 1st UTC
            return []  # no need to bother querying before beacon chain launch

        defi_events = []
        eth2_details = eth2.get_details(addresses=self.queried_addresses_for_module('eth2'))
        for entry in eth2_details:
            if entry.validator_index is None:
                continue  # don't query stats for validators without an index yet

            stats = eth2.get_validator_daily_stats(
                validator_index=entry.validator_index,
                msg_aggregator=self.msg_aggregator,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )
            for stats_entry in stats:
                got_asset = got_balance = spent_asset = spent_balance = None
                if stats_entry.pnl_balance.amount == ZERO:
                    continue

                if stats_entry.pnl_balance.amount > ZERO:
                    got_asset = A_ETH
                    got_balance = stats_entry.pnl_balance
                else:  # negative
                    spent_asset = A_ETH
                    spent_balance = -stats_entry.pnl_balance

                defi_events.append(DefiEvent(
                    timestamp=stats_entry.timestamp,
                    wrapped_event=stats_entry,
                    event_type=DefiEventType.ETH2_EVENT,
                    got_asset=got_asset,
                    got_balance=got_balance,
                    spent_asset=spent_asset,
                    spent_balance=spent_balance,
                    pnl=[AssetBalance(asset=A_ETH, balance=stats_entry.pnl_balance)],
                    count_spent_got_cost_basis=True,
                ))

        return defi_events

    @cache_response_timewise()
    def get_loopring_balances(self) -> Dict[Asset, Balance]:
        """Query loopring balances if the module is activated"""
        # Check if the loopring module is activated
        loopring_module = self.get_module('loopring')
        if loopring_module is None:
            return {}

        addresses = self.queried_addresses_for_module('loopring')
        balances = loopring_module.get_balances(addresses=addresses)

        # Now that we have balances for the addresses we need to aggregate the
        # assets in the different addresses
        aggregated_balances: Dict[Asset, Balance] = defaultdict(Balance)
        for _, assets in balances.items():
            for asset, balance in assets.items():
                aggregated_balances[asset] += balance

        return dict(aggregated_balances)
