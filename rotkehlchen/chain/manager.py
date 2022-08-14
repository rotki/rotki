import logging
from collections import defaultdict
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
    Union,
    overload,
)

from gevent.lock import Semaphore
from web3.exceptions import BadFunctionCallOutput

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.bitcoin import get_bitcoin_addresses_balances
from rotkehlchen.chain.bitcoin.bch import get_bitcoin_cash_addresses_balances
from rotkehlchen.chain.bitcoin.bch.utils import force_address_to_legacy_address
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.ethereum.defi.chad import DefiChad
from rotkehlchen.chain.ethereum.defi.structures import DefiProtocolBalances
from rotkehlchen.chain.ethereum.modules import (
    Aave,
    Adex,
    Balancer,
    Compound,
    Eth2,
    Liquity,
    Loopring,
    MakerdaoDsr,
    MakerdaoVaults,
    PickleFinance,
    Sushiswap,
    Uniswap,
    YearnVaults,
    YearnVaultsV2,
)
from rotkehlchen.chain.ethereum.modules.balancer.types import BalancerPoolBalance
from rotkehlchen.chain.ethereum.modules.eth2.structures import Eth2Validator
from rotkehlchen.chain.ethereum.tokens import EthTokens
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.substrate.manager import wait_until_a_node_is_available
from rotkehlchen.chain.substrate.types import KusamaAddress, PolkadotAddress
from rotkehlchen.chain.substrate.utils import SUBSTRATE_NODE_CONNECTION_TIMEOUT
from rotkehlchen.constants.assets import (
    A_ADX,
    A_AVAX,
    A_BCH,
    A_BTC,
    A_DAI,
    A_DOT,
    A_ETH,
    A_ETH2,
    A_KSM,
    A_LQTY,
)
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import (
    EthSyncError,
    InputError,
    ModuleInactive,
    ModuleInitializationFailure,
)
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import (
    BTCAddress,
    ChecksumEvmAddress,
    Eth2PubKey,
    ListOfBlockchainAddresses,
    Location,
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
    from rotkehlchen.chain.avalanche.manager import AvalancheManager
    from rotkehlchen.chain.ethereum.interfaces.ammswap.types import AddressToLPBalances
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.modules.balancer.types import AddressToPoolBalances
    from rotkehlchen.chain.ethereum.modules.eth2.structures import (
        Eth2Deposit,
        ValidatorDailyStats,
        ValidatorDetails,
    )
    from rotkehlchen.chain.ethereum.modules.nfts import Nfts
    from rotkehlchen.chain.ethereum.modules.uniswap.v3.types import AddressToUniswapV3LPBalances
    from rotkehlchen.chain.substrate.manager import SubstrateManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
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
DEFI_PROTOCOLS_TO_SKIP_LIABILITIES = {
    'Multi-Collateral Dai': True,  # True means all
    'Aave': True,
    'Aave V2': True,
    'Compound': True,
}


T = TypeVar('T')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BlockchainBalances:
    db: 'DBHandler'  # Need this to serialize BTC accounts with xpub mappings
    eth: DefaultDict[ChecksumEvmAddress, BalanceSheet] = field(init=False)
    eth2: DefaultDict[Eth2PubKey, BalanceSheet] = field(init=False)
    btc: Dict[BTCAddress, Balance] = field(init=False)
    bch: Dict[BTCAddress, Balance] = field(init=False)
    ksm: Dict[KusamaAddress, BalanceSheet] = field(init=False)
    dot: Dict[PolkadotAddress, BalanceSheet] = field(init=False)
    avax: DefaultDict[ChecksumEvmAddress, BalanceSheet] = field(init=False)

    def copy(self) -> 'BlockchainBalances':
        balances = BlockchainBalances(db=self.db)
        balances.eth = self.eth.copy()
        balances.eth2 = self.eth2.copy()
        balances.btc = self.btc.copy()
        balances.bch = self.bch.copy()
        balances.ksm = self.ksm.copy()
        balances.dot = self.dot.copy()
        balances.avax = self.avax.copy()
        return balances

    def __post_init__(self) -> None:
        self.eth = defaultdict(BalanceSheet)
        self.eth2 = defaultdict(BalanceSheet)
        self.btc = defaultdict(Balance)
        self.bch = defaultdict(Balance)
        self.ksm = defaultdict(BalanceSheet)
        self.dot = defaultdict(BalanceSheet)
        self.avax = defaultdict(BalanceSheet)

    def recalculate_totals(self) -> BalanceSheet:
        """Calculate and return new balance totals based on per-account data"""
        new_totals = BalanceSheet()
        for eth_balances in self.eth.values():
            new_totals += eth_balances
        for eth2_balances in self.eth2.values():
            new_totals += eth2_balances
        for btc_balance in self.btc.values():
            new_totals.assets[A_BTC] += btc_balance
        for bch_balance in self.bch.values():
            new_totals.assets[A_BTC] += bch_balance
        for ksm_balances in self.ksm.values():
            new_totals += ksm_balances
        for dot_balances in self.dot.values():
            new_totals += dot_balances
        for avax_balances in self.avax.values():
            new_totals += avax_balances
        return new_totals

    def serialize(self) -> Dict[str, Dict]:
        eth_balances = {k: v.serialize() for k, v in self.eth.items()}
        eth2_balances = {k: v.serialize() for k, v in self.eth2.items()}
        btc_balances: Dict[str, Any] = {}
        bch_balances: Dict[str, Any] = {}
        ksm_balances = {k: v.serialize() for k, v in self.ksm.items()}
        dot_balances = {k: v.serialize() for k, v in self.dot.items()}
        avax_balances = {k: v.serialize() for k, v in self.avax.items()}

        with self.db.conn.read_ctx() as cursor:
            btc_xpub_mappings = self.db.get_addresses_to_xpub_mapping(cursor, list(self.btc.keys()))  # noqa: E501
            bch_xpub_mappings = self.db.get_addresses_to_xpub_mapping(cursor, list(self.bch.keys()))  # noqa: E501

        self._serialize_bitcoin_balances(
            xpub_mappings=btc_xpub_mappings,
            bitcoin_balances=btc_balances,
            blockchain=SupportedBlockchain.BITCOIN,
        )
        self._serialize_bitcoin_balances(
            xpub_mappings=bch_xpub_mappings,
            bitcoin_balances=bch_balances,
            blockchain=SupportedBlockchain.BITCOIN_CASH,
        )

        blockchain_balances: Dict[str, Dict] = {}
        if eth_balances != {}:
            blockchain_balances['ETH'] = eth_balances
        if eth2_balances != {}:
            blockchain_balances['ETH2'] = eth2_balances
        if btc_balances != {}:
            blockchain_balances['BTC'] = btc_balances
        if bch_balances != {}:
            blockchain_balances['BCH'] = bch_balances
        if ksm_balances != {}:
            blockchain_balances['KSM'] = ksm_balances
        if dot_balances != {}:
            blockchain_balances['DOT'] = dot_balances
        if avax_balances != {}:
            blockchain_balances['AVAX'] = avax_balances

        return blockchain_balances

    def _serialize_bitcoin_balances(
        self,
        bitcoin_balances: Dict[str, Any],
        xpub_mappings: Dict[BTCAddress, XpubData],
        blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> None:
        """This is a helper function to serialize the balances for BTC & BCH accounts."""
        accounts_balances: Dict[BTCAddress, Balance] = getattr(self, blockchain.value.lower())
        for account, balances in accounts_balances.items():
            xpub_result = xpub_mappings.get(account, None)
            if xpub_result is None:
                if 'standalone' not in bitcoin_balances:
                    bitcoin_balances['standalone'] = {}

                addresses_dict = bitcoin_balances['standalone']
            else:
                if 'xpubs' not in bitcoin_balances:
                    bitcoin_balances['xpubs'] = []

                addresses_dict = None
                for xpub_entry in bitcoin_balances['xpubs']:
                    found = (
                        xpub_result.xpub.xpub == xpub_entry['xpub'] and
                        xpub_result.derivation_path == xpub_entry['derivation_path']
                    )
                    if found:
                        addresses_dict = xpub_entry['addresses']
                        break

                if addresses_dict is None:  # new xpub, create the mapping
                    btc_new_entry: Dict[str, Any] = {
                        'xpub': xpub_result.xpub.xpub,
                        'derivation_path': xpub_result.derivation_path,
                        'addresses': {},
                    }
                    bitcoin_balances['xpubs'].append(btc_new_entry)
                    addresses_dict = btc_new_entry['addresses']

            addresses_dict[account] = balances.serialize()


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
            polkadot_manager: 'SubstrateManager',
            avalanche_manager: 'AvalancheManager',
            msg_aggregator: MessagesAggregator,
            database: 'DBHandler',
            greenlet_manager: GreenletManager,
            premium: Optional[Premium],
            data_directory: Path,
            beaconchain: 'BeaconChain',
            btc_derivation_gap_limit: int,
            eth_modules: List[ModuleName],
    ):
        log.debug('Initializing ChainManager')
        super().__init__()
        self.ethereum = ethereum_manager
        self.kusama = kusama_manager
        self.polkadot = polkadot_manager
        self.avalanche = avalanche_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.accounts = blockchain_accounts
        self.data_directory = data_directory
        self.beaconchain = beaconchain
        self.btc_derivation_gap_limit = btc_derivation_gap_limit
        self.defi_balances_last_query_ts = Timestamp(0)
        self.defi_balances: Dict[ChecksumEvmAddress, List[DefiProtocolBalances]] = {}

        self.defi_lock = Semaphore()
        self.btc_lock = Semaphore()
        self.bch_lock = Semaphore()
        self.eth_lock = Semaphore()
        self.ksm_lock = Semaphore()
        self.dot_lock = Semaphore()
        self.avax_lock = Semaphore()

        # Per account balances
        self.balances = BlockchainBalances(db=database)
        # Per asset total balances
        self.totals: BalanceSheet = BalanceSheet()
        self.premium = premium
        self.greenlet_manager = greenlet_manager
        self.eth_modules: Dict[ModuleName, EthereumModule] = {}
        for given_module in eth_modules:
            self.activate_module(given_module)

        self.defichad = DefiChad(
            ethereum_manager=self.ethereum,
            msg_aggregator=self.msg_aggregator,
            database=self.database,
        )

    def __del__(self) -> None:
        del self.ethereum

    def set_ksm_rpc_endpoint(self, endpoint: str) -> Tuple[bool, str]:
        return self.kusama.set_rpc_endpoint(endpoint)

    def set_dot_rpc_endpoint(self, endpoint: str) -> Tuple[bool, str]:
        return self.polkadot.set_rpc_endpoint(endpoint)

    def activate_premium_status(self, premium: Premium) -> None:
        self.premium = premium
        for _, module in self.iterate_modules():
            if hasattr(module, 'premium') is True:
                module.premium = premium  # type: ignore

    def deactivate_premium_status(self) -> None:
        self.premium = None
        for _, module in self.iterate_modules():
            if hasattr(module, 'premium') is True and module.premium is not None:  # type: ignore  # noqa: E501
                module.premium = None  # type: ignore

    def process_new_modules_list(self, module_names: List[ModuleName]) -> None:
        """Processes a new list of active modules

        Adds those missing, and removes those not present
        """
        existing_names = set(self.eth_modules.keys())
        given_modules_set = set(module_names)
        modules_to_remove = existing_names.difference(given_modules_set)
        modules_to_add = given_modules_set.difference(existing_names)

        with self.eth_lock:
            for name in modules_to_remove:
                self.deactivate_module(name)
            for name in modules_to_add:
                self.activate_module(name)

    def iterate_modules(self) -> Iterator[Tuple[str, EthereumModule]]:
        for name, module in self.eth_modules.items():
            yield name, module

    def queried_addresses_for_module(self, module: ModuleName) -> List[ChecksumEvmAddress]:
        """Returns the addresses to query for the given module/protocol"""
        with self.database.conn.read_ctx() as cursor:
            result = QueriedAddresses(self.database).get_queried_addresses_for_module(cursor, module)  # noqa: E501
        return result if result is not None else self.accounts.eth

    def activate_module(self, module_name: ModuleName) -> Optional[EthereumModule]:
        """Activates an ethereum module by module name"""
        module = self.eth_modules.get(module_name, None)
        if module:
            return module  # already activated

        log.debug(f'Activating {module_name} module')
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
            log.error(f'Failed to activate {module_name} due to: {str(e)}')
            return None

        self.eth_modules[module_name] = instance
        if instance.on_startup is not None:  # run startup initialization actions for the module
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

        log.debug(f'Deactivating {module_name} module')
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
    def get_module(self, module_name: Literal['sushiswap']) -> Optional[Sushiswap]:
        ...

    @overload
    def get_module(self, module_name: Literal['yearn_vaults']) -> Optional[YearnVaults]:
        ...

    @overload
    def get_module(self, module_name: Literal['yearn_vaults_v2']) -> Optional[YearnVaultsV2]:
        ...

    @overload
    def get_module(self, module_name: Literal['liquity']) -> Optional[Liquity]:
        ...

    @overload
    def get_module(self, module_name: Literal['pickle_finance']) -> Optional[PickleFinance]:
        ...

    @overload
    def get_module(self, module_name: Literal['nfts']) -> Optional['Nfts']:
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

    def check_accounts_existence(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
            append_or_remove: Literal['append', 'remove'],
    ) -> None:
        """Checks if any of the accounts already exist or don't exist
        (depending on `append_or_remove`) and may raise an InputError"""
        if blockchain == SupportedBlockchain.BITCOIN_CASH and append_or_remove == 'append':
            with self.database.conn.read_ctx() as cursor:
                bch_accounts = self.database.get_blockchain_account_data(
                    cursor=cursor,
                    blockchain=blockchain,
                )
                forced_bch_legacy_addresses = {
                    force_address_to_legacy_address(account.address)
                    for account in bch_accounts
                }

        bad_accounts = []
        for account in accounts:
            if blockchain == SupportedBlockchain.BITCOIN_CASH and append_or_remove == 'append':
                # an already existing bch address can be added but in a different format
                # so convert all bch addresses to the same format and compare.
                existent = account in self.accounts.bch or force_address_to_legacy_address(account) in forced_bch_legacy_addresses  # noqa: E501
            else:
                existent = account in self.accounts.get(blockchain)

            if existent is True and append_or_remove == 'append':
                bad_accounts.append(account)
            elif existent is False and append_or_remove == 'remove':
                bad_accounts.append(account)

        if len(bad_accounts) != 0:
            word = 'already' if append_or_remove == 'append' else 'don\'t'
            raise InputError(
                f'Blockchain account/s {",".join(bad_accounts)} {word} exist',
            )

    @protect_with_lock(arguments_matter=True)
    @cache_response_timewise(forward_ignore_cache=True)
    def query_balances(
            self,
            blockchain: Optional[SupportedBlockchain] = None,
            beaconchain_fetch_eth1: bool = False,
            ignore_cache: bool = False,
    ) -> BlockchainBalancesUpdate:
        """Queries either all, or specific blockchain balances

        If querying beaconchain and beaconchain_fetch_eth1 is true then each eth1 address is also
        checked for the validators it has deposited and the deposits are fetched.

        May raise:
        - RemoteError if an external service such as Etherscan or blockchain.info
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        should_query_eth = not blockchain or blockchain == SupportedBlockchain.ETHEREUM
        should_query_eth2 = not blockchain or blockchain == SupportedBlockchain.ETHEREUM_BEACONCHAIN  # noqa: E501
        should_query_btc = not blockchain or blockchain == SupportedBlockchain.BITCOIN
        should_query_bch = not blockchain or blockchain == SupportedBlockchain.BITCOIN_CASH
        should_query_ksm = not blockchain or blockchain == SupportedBlockchain.KUSAMA
        should_query_dot = not blockchain or blockchain == SupportedBlockchain.POLKADOT
        should_query_avax = not blockchain or blockchain == SupportedBlockchain.AVALANCHE

        if should_query_eth:
            self.query_ethereum_balances(
                ignore_cache=ignore_cache,
            )
        if should_query_eth2:
            self.query_ethereum_beaconchain_balances(
                fetch_validators_for_eth1=beaconchain_fetch_eth1,  # document this better
                ignore_cache=ignore_cache,
            )
        if should_query_btc:
            self.query_btc_balances(ignore_cache=ignore_cache)
        if should_query_bch:
            self.query_bch_balances(ignore_cache=ignore_cache)
        if should_query_ksm:
            self.query_kusama_balances(ignore_cache=ignore_cache)
        if should_query_dot:
            self.query_polkadot_balances(ignore_cache=ignore_cache)
        if should_query_avax:
            self.query_avax_balances(ignore_cache=ignore_cache)

        self.totals = self.balances.recalculate_totals()
        return self.get_balances_update()

    @protect_with_lock()
    @cache_response_timewise()
    def query_btc_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """Queries blockchain.info/blockstream for the balance of all BTC accounts

        May raise:
        - RemotError if there is a problem querying any remote
        """
        if len(self.accounts.btc) == 0:
            return

        self.balances.btc = {}
        btc_usd_price = Inquirer().find_usd_price(A_BTC)
        balances = get_bitcoin_addresses_balances(self.accounts.btc)
        for account, balance in balances.items():
            self.balances.btc[account] = Balance(
                amount=balance,
                usd_value=balance * btc_usd_price,
            )

    @protect_with_lock()
    @cache_response_timewise()
    def query_bch_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """Queries api.haskoin.com for the balance of all BCH accounts

        May raise:
        - RemotError if there is a problem querying any remote
        """
        if len(self.accounts.bch) == 0:
            return

        self.balances.bch = {}
        bch_usd_price = Inquirer().find_usd_price(A_BCH)
        balances = get_bitcoin_cash_addresses_balances(self.accounts.bch)
        for account, balance in balances.items():
            self.balances.bch[account] = Balance(
                amount=balance,
                usd_value=balance * bch_usd_price,
            )

    @protect_with_lock()
    @cache_response_timewise()
    def query_kusama_balances(
            self,  # pylint: disable=unused-argument
            wait_available_node: bool = True,
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
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
                seconds=SUBSTRATE_NODE_CONNECTION_TIMEOUT,
            )

        account_amount = self.kusama.get_accounts_balance(self.accounts.ksm)
        for account, amount in account_amount.items():
            balance = Balance(
                amount=amount,
                usd_value=amount * ksm_usd_price,
            )
            self.balances.ksm[account] = BalanceSheet(
                assets=defaultdict(Balance, {A_KSM: balance}),
            )

    @protect_with_lock()
    @cache_response_timewise()
    def query_avax_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """Queries the AVAX balances of the accounts via Avalanche/Covalent endpoints.
        May raise:
        - RemotError: if no nodes are available or the balances request fails.
        """
        if len(self.accounts.avax) == 0:
            return

        # Query avax balance
        avax_usd_price = Inquirer().find_usd_price(A_AVAX)
        account_amount = self.avalanche.get_multiavax_balance(self.accounts.avax)
        for account, amount in account_amount.items():
            usd_value = amount * avax_usd_price
            self.balances.avax[account] = BalanceSheet(
                assets=defaultdict(Balance, {A_AVAX: Balance(amount, usd_value)}),
            )

    @protect_with_lock()
    @cache_response_timewise()
    def query_polkadot_balances(
            self,  # pylint: disable=unused-argument
            wait_available_node: bool = True,
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """Queries the DOT balances of the accounts via Polkadot endpoints.

        May raise:
        - RemotError: if no nodes are available or the balances request fails.
        """
        if len(self.accounts.dot) == 0:
            return

        dot_usd_price = Inquirer().find_usd_price(A_DOT)
        if wait_available_node:
            wait_until_a_node_is_available(
                substrate_manager=self.polkadot,
                seconds=SUBSTRATE_NODE_CONNECTION_TIMEOUT,
            )

        account_amount = self.polkadot.get_accounts_balance(self.accounts.dot)
        for account, amount in account_amount.items():
            balance = Balance(
                amount=amount,
                usd_value=amount * dot_usd_price,
            )
            self.balances.dot[account] = BalanceSheet(
                assets=defaultdict(Balance, {A_DOT: balance}),
            )

    def sync_bitcoin_accounts_with_db(
            self,
            cursor: 'DBCursor',
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> None:
        """Call this function after having deleted BTC/BCH accounts from the DB to
        sync the chain manager's balances and accounts with the DB

        For example this is called after removing an xpub which deletes all derived
        addresses from the DB.
        """
        db_btc_accounts = getattr(
            self.database.get_blockchain_accounts(cursor),
            blockchain.value.lower(),
        )
        accounts_to_remove = []
        for account in getattr(self.accounts, blockchain.value.lower()):
            if account not in db_btc_accounts:
                accounts_to_remove.append(account)

        self.modify_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts_to_remove,
            append_or_remove='remove',
        )

    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> None:
        """Adds new blockchain accounts.
        The accounts are added in the blockchain object and not in the database.

        May Raise:
        - InputError if the given accounts list is empty, or if it contains invalid accounts,
          or if any account already exists.
        """
        if len(accounts) == 0:
            raise InputError('Empty list of blockchain accounts to add was given')

        self.modify_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
            append_or_remove='append',
        )

    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> None:
        """Removes blockchain accounts.

        The accounts are removed from the blockchain object and not from the database.
        Database removal happens afterwards at the caller.

        If any of the given accounts are not known an inputError is raised and
        no account is modified.

        May Raise:
        - InputError if the given accounts list is empty, or if
        it contains an unknown account or invalid account
        """
        if len(accounts) == 0:
            raise InputError('Empty list of blockchain accounts to remove was given')

        unknown_accounts = set(accounts).difference(self.accounts.get(blockchain))
        if len(unknown_accounts) != 0:
            raise InputError(
                f'Tried to remove unknown {blockchain.value} '
                f'accounts {",".join(unknown_accounts)}',
            )

        self.modify_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts,
            append_or_remove='remove',
        )

    def modify_dot_ksm_accounts(
            self,
            accounts: Union[List[PolkadotAddress], List[KusamaAddress]],
            blockchain: Literal[SupportedBlockchain.POLKADOT, SupportedBlockchain.KUSAMA],
            append_or_remove: Literal['append', 'remove'],
    ) -> None:
        """May raise:
        - RemoteError if we couldn't connect to any node"""
        lock: Semaphore = getattr(self, f'{blockchain.value.lower()}_lock')
        address_type = blockchain.get_address_type()
        substrate_manager: 'SubstrateManager' = getattr(self, blockchain.name.lower())
        saved_accounts = self.accounts.get(blockchain=blockchain)
        balances: Union[Dict[PolkadotAddress, BalanceSheet], Dict[KusamaAddress, BalanceSheet]]
        balances = getattr(self.balances, blockchain.value.lower())

        with lock:
            # we are adding/removing accounts, make sure query cache is flushed
            self.flush_cache(f'query_{blockchain.name.lower()}_balances')

            if append_or_remove == 'append':
                # When adding account for the first time we should connect to the nodes
                if len(substrate_manager.available_nodes_call_order) == 0:
                    substrate_manager.attempt_connections()
                    wait_until_a_node_is_available(
                        substrate_manager=substrate_manager,
                        seconds=SUBSTRATE_NODE_CONNECTION_TIMEOUT,
                    )

            for account in accounts:
                address = address_type(account)
                if append_or_remove == 'append':
                    saved_accounts.append(address)
                else:  # remove
                    balances.pop(address, None)
                    saved_accounts.remove(address)

    def modify_btc_bch_avax_accounts(
            self,
            accounts: Union[List[BTCAddress], List[ChecksumEvmAddress]],
            blockchain: Literal[
                SupportedBlockchain.BITCOIN,
                SupportedBlockchain.BITCOIN_CASH,
                SupportedBlockchain.AVALANCHE,
            ],
            append_or_remove: Literal['append', 'remove'],
    ) -> None:
        # we are adding/removing accounts, make sure query cache is flushed
        self.flush_cache(f'query_{blockchain.value.lower()}_balances')

        address_type = blockchain.get_address_type()
        saved_accounts = self.accounts.get(blockchain=blockchain)
        balances = getattr(self.balances, blockchain.value.lower())

        for account in accounts:
            address = address_type(account)
            if append_or_remove == 'append':
                saved_accounts.append(address)
            else:  # remove
                balances.pop(address, None)
                saved_accounts.remove(address)

    def modify_eth_accounts(
            self,
            accounts: List[ChecksumEvmAddress],
            append_or_remove: Literal['append', 'remove'],
    ) -> None:
        """May raise:
        - RemoteError if there is a problem querying an external service such
          as etherscan (from on_account_addition or on_account_removal callback)"""
        with self.eth_lock:
            # we are adding/removing accounts, make sure query cache is flushed
            self.flush_cache('query_ethereum_balances')

            for account in accounts:
                address = string_to_evm_address(account)
                if append_or_remove == 'append':
                    self.accounts.eth.append(address)
                    for _, module in self.iterate_modules():
                        module.on_account_addition(address)
                else:  # remove
                    self.balances.eth.pop(address, None)
                    self.accounts.eth.remove(address)
                    self.defi_balances.pop(address, None)
                    for _, module in self.iterate_modules():
                        module.on_account_removal(address)

    def modify_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
            append_or_remove: Literal['append', 'remove'],
    ) -> None:
        """Add or remove a list of blockchain accounts.

       May raise:
        - InputError if any of the accounts exists while trying to append or any of the
        accounts doesn't exist while trying to remove
        - RemoteError if there is a problem querying an external service such
          as etherscan or blockchain.info or couldn't connect to a node (for polkadot and kusama)
        """
        self.check_accounts_existence(
            blockchain=blockchain,
            accounts=accounts,
            append_or_remove=append_or_remove,
        )

        if blockchain in {
            SupportedBlockchain.BITCOIN,
            SupportedBlockchain.BITCOIN_CASH,
            SupportedBlockchain.AVALANCHE,
        }:
            # we use `type: ignore` here and in other methods since mypy doesn't understand that
            # types of `blockchain` and `accounts` can be narrowed after if checks
            self.modify_btc_bch_avax_accounts(
                accounts=accounts,  # type: ignore
                blockchain=blockchain,  # type: ignore
                append_or_remove=append_or_remove,
            )

        elif blockchain == SupportedBlockchain.ETHEREUM:
            self.modify_eth_accounts(
                accounts=accounts,  # type: ignore
                append_or_remove=append_or_remove,
            )

        elif blockchain in {SupportedBlockchain.POLKADOT, SupportedBlockchain.KUSAMA}:
            self.modify_dot_ksm_accounts(
                accounts=accounts,  # type: ignore
                blockchain=blockchain,  # type: ignore
                append_or_remove=append_or_remove,
            )

        else:
            # That should not happen. Should be checked by marshmallow
            raise AssertionError(
                'Unsupported blockchain {} provided at remove_blockchain_account'.format(
                    blockchain),
            )

        # we are adding/removing accounts, make sure query cache is flushed
        self.flush_cache('query_balances')
        self.flush_cache('query_balances', blockchain=blockchain)

        # recalculate totals
        if append_or_remove == 'remove':  # at addition no balances are queried so no need
            self.totals = self.balances.recalculate_totals()

    @protect_with_lock()
    @cache_response_timewise()
    def query_ethereum_beaconchain_balances(
            self,  # pylint: disable=unused-argument
            fetch_validators_for_eth1: bool,
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """Queries ethereum beacon chain balances

        May raise:
        - RemoteError if an external service such as beaconchain
        is queried and there is a problem with its query.
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            return  # no eth2 module active -- do nothing

        # Before querying the new balances, delete the ones in memory if any
        self.balances.eth2.clear()
        balance_mapping = eth2.get_balances(
            addresses=self.queried_addresses_for_module('eth2'),
            fetch_validators_for_eth1=fetch_validators_for_eth1,
        )
        for pubkey, balance in balance_mapping.items():
            self.balances.eth2[pubkey] = BalanceSheet(
                assets=defaultdict(Balance, {A_ETH2: balance}),
            )

    def _update_balances_after_token_query(
            self,
            dsr_proxy_append: bool,
            balance_result: Dict[ChecksumEvmAddress, Dict[EvmToken, FVal]],
            token_usd_price: Dict[EvmToken, Price],
    ) -> None:
        # Update the per account token balance and usd value
        eth_balances = self.balances.eth
        for account, token_balances in balance_result.items():
            for token, token_balance in token_balances.items():
                balance = Balance(
                    amount=token_balance,
                    usd_value=token_balance * token_usd_price[token],
                )
                if dsr_proxy_append is True:
                    eth_balances[account].assets[token] += balance
                else:
                    eth_balances[account].assets[token] = balance

    def query_ethereum_tokens(self) -> None:
        """Queries ethereum token balance via either etherscan or ethereum node

        Should come here during addition of a new account or querying of all token
        balances.

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        ethtokens = EthTokens(database=self.database, ethereum=self.ethereum)
        try:
            balance_result, token_usd_price = ethtokens.query_tokens_for_addresses(
                addresses=self.accounts.eth,
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

        self._update_balances_after_token_query(
            dsr_proxy_append=False,
            balance_result=balance_result,
            token_usd_price=token_usd_price,
        )

    def query_defi_balances(self) -> Dict[ChecksumEvmAddress, List[DefiProtocolBalances]]:
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
    def query_ethereum_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
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
        for account, balance in balances.items():
            usd_value = balance * eth_usd_price
            self.balances.eth[account] = BalanceSheet(
                assets=defaultdict(Balance, {A_ETH: Balance(balance, usd_value)}),
            )

        self.query_defi_balances()
        self.query_ethereum_tokens()
        self._add_protocol_balances()

    def query_ethereum_lp_balances(
            self,
            balances: Dict[str, Dict[Asset, Balance]],
    ) -> Optional['AddressToUniswapV3LPBalances']:
        """Queries all ethereum liquidity pool balances and adds them to the balances.
        Returns the Uniswap V3 LP balances as they're needed for the NFTs balances.
        May raise:
        - RemoteError if any of the calls fail.
        """
        module_names: List[Literal['sushiswap', 'balancer']] = ['sushiswap', 'balancer']
        uniswap = self.get_module('uniswap')
        uniswap_v3_balances = None
        if uniswap is not None:
            uniswap_v3_balances = uniswap.get_v3_balances(
                addresses=self.queried_addresses_for_module('uniswap'),
            )
            uniswap_v2_balances = uniswap.get_balances(
                addresses=self.queried_addresses_for_module('uniswap'),
            )
            self.add_ethereum_lp_to_balance(
                lp_balance=uniswap_v2_balances,
                balances=balances,
            )

        for module_name in module_names:
            module = self.get_module(module_name)
            if module is not None:
                module_lp_balances = module.get_balances(
                    addresses=self.queried_addresses_for_module(module_name),
                )
                self.add_ethereum_lp_to_balance(
                    lp_balance=module_lp_balances,
                    balances=balances,
                )

        return uniswap_v3_balances

    def add_ethereum_lp_to_balance(
            self,
            lp_balance: Union['AddressToPoolBalances', 'AddressToLPBalances'],
            balances: Dict[str, Dict[Asset, Balance]],
    ) -> None:
        """Adds the liquidity pool balance(one of Uniswap, Sushiswap or Balancer) to the
        blockchain balances.
        """
        if len(lp_balance) == 0:
            return

        loc_key = str(Location.BLOCKCHAIN)
        if loc_key not in balances:
            balances[loc_key] = {}

        for lps in lp_balance.values():
            for lp in lps:
                if isinstance(lp, BalancerPoolBalance):
                    balances[loc_key][lp.pool_token] = lp.user_balance
                else:
                    balances[loc_key][EvmToken(ethaddress_to_identifier(lp.address))] = lp.user_balance  # noqa: E501

    def _add_protocol_balances(self) -> None:
        """Also count token balances that may come from various protocols"""
        # If we have anything in DSR also count it towards total blockchain balances
        eth_balances = self.balances.eth
        dsr_module = self.get_module('makerdao_dsr')
        if dsr_module is not None:
            current_dsr_report = dsr_module.get_current_dsr()
            for dsr_account, balance_entry in current_dsr_report.balances.items():

                if balance_entry.amount == ZERO:
                    continue

                eth_balances[dsr_account].assets[A_DAI] += balance_entry

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

            proxy_mappings = vaults_module._get_accounts_having_proxy()
            proxy_to_address = {}
            proxy_addresses = []
            for user_address, proxy_address in proxy_mappings.items():
                proxy_to_address[proxy_address] = user_address
                proxy_addresses.append(proxy_address)

            ethtokens = EthTokens(database=self.database, ethereum=self.ethereum)
            try:
                balance_result, token_usd_price = ethtokens.query_tokens_for_addresses(
                    addresses=proxy_addresses,
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
                dsr_proxy_append=True,
                balance_result=new_result,
                token_usd_price=token_usd_price,
            )

            # also query defi balances to get liabilities
            defi_balances_map = self.defichad.query_defi_balances(proxy_addresses)
            for proxy_address, defi_balances in defi_balances_map.items():
                self._add_account_defi_balances_to_token(
                    account=proxy_to_address[proxy_address],
                    balances=defi_balances,
                )

        adex_module = self.get_module('adex')
        if adex_module is not None and self.premium is not None:
            adex_balances = adex_module.get_balances(addresses=self.queried_addresses_for_module('adex'))  # noqa: E501
            for address, balance in adex_balances.items():
                eth_balances[address].assets[A_ADX] += balance

        pickle_module = self.get_module('pickle_finance')
        if pickle_module is not None:
            pickle_balances_per_address = pickle_module.balances_in_protocol(
                addresses=self.queried_addresses_for_module('pickle_finance'),
            )
            for address, pickle_balances in pickle_balances_per_address.items():
                for asset_balance in pickle_balances:
                    eth_balances[address].assets[asset_balance.asset] += asset_balance.balance

        liquity_module = self.get_module('liquity')
        if liquity_module is not None:
            # Get trove information
            liquity_balances = liquity_module.get_positions(
                addresses_list=self.queried_addresses_for_module('liquity'),
            )
            for address, deposits in liquity_balances.items():
                collateral = deposits.collateral.balance
                eth_balances[address].assets[A_ETH] += collateral
            # Get staked amounts
            liquity_staked = liquity_module.liquity_staking_balances(
                addresses=self.queried_addresses_for_module('liquity'),
            )
            for address, staked_info in liquity_staked.items():
                deposited_lqty = staked_info.staked.balance
                eth_balances[address].assets[A_LQTY] += deposited_lqty

        # Finally count the balances detected in various protocols in defi balances
        self.add_defi_balances_to_account()

    def _add_account_defi_balances_to_token(
            self,
            account: ChecksumEvmAddress,
            balances: List[DefiProtocolBalances],
    ) -> None:
        """Add a single account's defi balances to per account"""
        for entry in balances:
            found_double_entry = False
            # filter our specific protocols for double entries
            for skip_mapping, balance_type in (
                    (DEFI_PROTOCOLS_TO_SKIP_ASSETS, 'Asset'),
                    (DEFI_PROTOCOLS_TO_SKIP_LIABILITIES, 'Debt'),
            ):
                skip_list = skip_mapping.get(entry.protocol.name, None)  # type: ignore
                double_entry = (
                    entry.balance_type == balance_type and
                    skip_list and
                    (skip_list is True or entry.base_balance.token_symbol in skip_list)
                )
                if double_entry:
                    found_double_entry = True
                    break

            if found_double_entry:
                continue

            if entry.balance_type == 'Asset' and entry.base_balance.token_symbol == 'ETH':
                # If ETH appears as asset here I am not sure how to handle, so ignore for now
                log.warning(
                    f'Found ETH in DeFi balances for account: {account} and '
                    f'protocol: {entry.protocol.name}. Ignoring ...',
                )
                continue

            try:
                token = EvmToken(ethaddress_to_identifier(entry.base_balance.token_address))
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
            elif entry.balance_type == 'Debt':
                log.debug(f'Adding DeFi debt balance for {token} {entry.base_balance.balance}')
                eth_balances[account].liabilities[token] += entry.base_balance.balance
            else:
                log.warning(  # type: ignore # is an unreachable statement but we are defensive
                    f'Zerion Defi Adapter returned unknown asset type {entry.balance_type}. '
                    f'Skipping ...',
                )
                continue

    def add_defi_balances_to_account(self) -> None:
        """Take into account defi balances and add them to the per account balances"""
        for account, defi_balances in self.defi_balances.items():
            self._add_account_defi_balances_to_token(
                account=account,
                balances=defi_balances,
            )

    @protect_with_lock()
    @cache_response_timewise()
    def get_eth2_staking_deposits(self) -> List['Eth2Deposit']:
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive(
                'Could not query eth2 staking deposits since eth2 module is not active',
            )
        deposits = eth2.get_staking_deposits(
            addresses=self.queried_addresses_for_module('eth2'),
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

    def get_eth2_daily_stats(
            self,
            filter_query: Eth2DailyStatsFilterQuery,
            only_cache: bool,
    ) -> Tuple[List['ValidatorDailyStats'], int, FVal, FVal]:
        """May raise:
        - ModuleInactive if eth2 module is not activated
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant query eth2 daily stats details since eth2 module is not active')  # noqa: E501
        with self.database.conn.read_ctx() as cursor:
            return eth2.get_validator_daily_stats(
                cursor=cursor,
                filter_query=filter_query,
                only_cache=only_cache,
                msg_aggregator=self.msg_aggregator,
            )

    @protect_with_lock()
    @cache_response_timewise()
    def get_eth2_history_events(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> List['ValidatorDailyStats']:
        """May raise:
        - ModuleInactive if eth2 module is not activated
        - RemoteError if a remote query to beacon chain fails and is not caught in the method
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant query eth2 history events since eth2 module is not active')

        if to_timestamp < 1607212800:  # Dec 1st UTC
            return []  # no need to bother querying before beacon chain launch

        # Ask for details to detect any new validators
        eth2.get_details(addresses=self.queried_addresses_for_module('eth2'))
        # Create a mapping of validator index to ownership proportion
        validators_ownership = {
            validator.index: validator.ownership_proportion
            for validator in self.get_eth2_validators()
        }
        # And now get all daily stats and create defi events for them
        with self.database.conn.read_ctx() as cursor:
            stats, _, _, _ = eth2.get_validator_daily_stats(
                cursor=cursor,
                filter_query=Eth2DailyStatsFilterQuery.make(from_ts=from_timestamp, to_ts=to_timestamp),  # noqa: E501
                only_cache=False,
                msg_aggregator=self.msg_aggregator,
            )
        for stats_entry in stats:
            if stats_entry.pnl_balance.amount == ZERO:
                continue

            # Take into account the validator ownership proportion if is not 100%
            validator_ownership = validators_ownership.get(stats_entry.validator_index, ONE)
            if validator_ownership != ONE:
                stats_entry.pnl = stats_entry.pnl * validator_ownership
                stats_entry.ownership_percentage = validator_ownership

        return stats

    def get_eth2_validators(self) -> List[Eth2Validator]:
        """May raise:
        - ModuleInactive if eth2 module is not activated
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant get eth2 validators since the eth2 module is not active')
        with self.database.conn.read_ctx() as cursor:
            return DBEth2(self.database).get_validators(cursor)

    def edit_eth2_validator(self, validator_index: int, ownership_proportion: FVal) -> None:
        """Edit a validator to modify its ownership proportion. May raise:
        - ModuleInactive if eth2 module is not active
        - InputError if no row was affected
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant edit eth2 validators since the eth2 module is not active')
        DBEth2(self.database).edit_validator(
            validator_index=validator_index,
            ownership_proportion=ownership_proportion,
        )
        self.flush_cache('get_eth2_daily_stats')
        self.flush_cache('query_ethereum_beaconchain_balances')
        self.flush_cache('query_balances')
        self.flush_cache('query_balances', blockchain=SupportedBlockchain.ETHEREUM_BEACONCHAIN)

    def add_eth2_validator(
            self,
            validator_index: Optional[int],
            public_key: Optional[Eth2PubKey],
            ownership_proportion: FVal,
    ) -> None:
        """May raise:
        - ModuleInactive if eth2 module is not activated
        - RemoteError if there is a problem querying beaconcha.in
        - PremiumPermissionError if adding the validator would go over free limit
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant add eth2 validator since eth2 module is not active')
        with self.database.user_write() as cursor:
            eth2.add_validator(
                write_cursor=cursor,
                validator_index=validator_index,
                public_key=public_key,
                ownership_proportion=ownership_proportion,
            )
        self.flush_cache('get_eth2_staking_deposits')
        self.flush_cache('get_eth2_staking_details')
        self.flush_cache('get_eth2_history_events')
        self.flush_cache('get_eth2_daily_stats')
        self.flush_cache('query_ethereum_beaconchain_balances')
        self.flush_cache('query_balances')
        self.flush_cache('query_balances', blockchain=SupportedBlockchain.ETHEREUM_BEACONCHAIN)

    def delete_eth2_validator(
            self,
            validator_index: Optional[int],
            public_key: Optional[str],
    ) -> None:
        """May raise:
        - ModuleInactive if eth2 module is not activated
        - InputError if the validator is not found in the DB
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant delete eth2 validator since eth2 module is not active')
        return DBEth2(self.database).delete_validator(
            validator_index=validator_index,
            public_key=public_key,
        )

    @cache_response_timewise()
    def get_loopring_balances(self) -> Dict[Asset, Balance]:
        """Query loopring balances if the module is activated

        May raise:
        - RemoteError if there is problems querying loopring api
        """
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
