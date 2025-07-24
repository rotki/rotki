import logging
import operator
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from functools import reduce
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, TypeVar, cast, get_args, overload

import requests
from gevent.lock import Semaphore
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput, Web3Exception

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.accounts import BlockchainAccountData, BlockchainAccounts
from rotkehlchen.chain.arbitrum_one.modules.gearbox.balances import (
    GearboxBalances as GearboxBalancesArbitrumOne,
)
from rotkehlchen.chain.arbitrum_one.modules.gmx.balances import GmxBalances
from rotkehlchen.chain.arbitrum_one.modules.hyperliquid.balances import (
    HyperliquidBalances,
)
from rotkehlchen.chain.arbitrum_one.modules.thegraph.balances import (
    ThegraphBalances as ThegraphBalancesArbitrumOne,
)
from rotkehlchen.chain.arbitrum_one.modules.umami.balances import UmamiBalances
from rotkehlchen.chain.balances import BlockchainBalances, BlockchainBalancesUpdate
from rotkehlchen.chain.base.modules.aerodrome.balances import AerodromeBalances
from rotkehlchen.chain.base.modules.extrafi.balances import (
    ExtrafiBalances as ExtrafiBalancesBase,
)
from rotkehlchen.chain.bitcoin.bch.utils import force_address_to_legacy_address
from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.chain.constants import SAFE_BASIC_ABI
from rotkehlchen.chain.ethereum.modules import MODULE_NAME_TO_PATH
from rotkehlchen.chain.ethereum.modules.aave.balances import AaveBalances
from rotkehlchen.chain.ethereum.modules.blur.balances import BlurBalances
from rotkehlchen.chain.ethereum.modules.convex.balances import ConvexBalances
from rotkehlchen.chain.ethereum.modules.curve.balances import CurveBalances
from rotkehlchen.chain.ethereum.modules.curve.crvusd.balances import CurveCrvusdBalances
from rotkehlchen.chain.ethereum.modules.eigenlayer.balances import EigenlayerBalances
from rotkehlchen.chain.ethereum.modules.gearbox.balances import GearboxBalances
from rotkehlchen.chain.ethereum.modules.hedgey.balances import HedgeyBalances
from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.chain.ethereum.modules.makerdao.constants import CPT_DSR, CPT_VAULT
from rotkehlchen.chain.ethereum.modules.octant.balances import OctantBalances
from rotkehlchen.chain.ethereum.modules.pendle.balances import PendleBalances
from rotkehlchen.chain.ethereum.modules.pickle_finance.constants import CPT_PICKLE
from rotkehlchen.chain.ethereum.modules.safe.balances import SafeBalances
from rotkehlchen.chain.ethereum.modules.thegraph.balances import ThegraphBalances
from rotkehlchen.chain.evm.decoding.compound.v3.balances import Compoundv3Balances
from rotkehlchen.chain.evm.decoding.curve.lend.balances import CurveLendBalances
from rotkehlchen.chain.evm.decoding.hop.balances import HopBalances
from rotkehlchen.chain.evm.decoding.uniswap.v3.balances import UniswapV3Balances
from rotkehlchen.chain.gnosis.modules.giveth.balances import GivethBalances as GivethGnosisBalances
from rotkehlchen.chain.optimism.modules.extrafi.balances import (
    ExtrafiBalances as ExtrafiBalancesOp,
)
from rotkehlchen.chain.optimism.modules.gearbox.balances import (
    GearboxBalances as GearboxBalancesOptimism,
)
from rotkehlchen.chain.optimism.modules.giveth.balances import (
    GivethBalances as GivethOptimismBalances,
)
from rotkehlchen.chain.optimism.modules.velodrome.balances import VelodromeBalances
from rotkehlchen.chain.optimism.modules.walletconnect.balances import WalletconnectBalances
from rotkehlchen.chain.substrate.manager import wait_until_a_node_is_available
from rotkehlchen.chain.substrate.utils import SUBSTRATE_NODE_CONNECTION_TIMEOUT
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ONE, ZERO
from rotkehlchen.constants.assets import A_AVAX, A_BCH, A_BTC, A_DAI, A_DOT, A_ETH, A_ETH2, A_KSM
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import (
    EthSyncError,
    InputError,
    ModuleInactive,
    ModuleInitializationFailure,
    RemoteError,
)
from rotkehlchen.externalapis.etherscan import HasChainActivity
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import (
    CHAIN_IDS_WITH_BALANCE_PROTOCOLS,
    CHAINS_WITH_CHAIN_MANAGER,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS_TYPE,
    SUPPORTED_EVM_EVMLIKE_CHAINS,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    SUPPORTED_SUBSTRATE_CHAINS,
    BlockchainAddress,
    ChainID,
    ChecksumEvmAddress,
    Eth2PubKey,
    ListOfBlockchainAddresses,
    ModuleName,
    Price,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule, ProgressUpdater
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn, cache_response_timewise
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.manager import ArbitrumOneManager
    from rotkehlchen.chain.avalanche.manager import AvalancheManager
    from rotkehlchen.chain.base.manager import BaseManager
    from rotkehlchen.chain.binance_sc.manager import BinanceSCManager
    from rotkehlchen.chain.bitcoin.bch.manager import BitcoinCashManager
    from rotkehlchen.chain.bitcoin.btc.manager import BitcoinManager
    from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithBalance
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
    from rotkehlchen.chain.ethereum.modules.eth2.structures import (
        ValidatorDailyStats,
        ValidatorDetailsWithStatus,
    )
    from rotkehlchen.chain.ethereum.modules.l2.loopring import Loopring
    from rotkehlchen.chain.ethereum.modules.liquity.trove import Liquity
    from rotkehlchen.chain.ethereum.modules.makerdao.dsr import MakerdaoDsr
    from rotkehlchen.chain.ethereum.modules.makerdao.vaults import MakerdaoVaults
    from rotkehlchen.chain.ethereum.modules.nft.nfts import Nfts
    from rotkehlchen.chain.ethereum.modules.pickle_finance.main import PickleFinance
    from rotkehlchen.chain.ethereum.modules.sushiswap.sushiswap import Sushiswap
    from rotkehlchen.chain.ethereum.modules.uniswap.uniswap import Uniswap
    from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.manager import EvmManager
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.gnosis.manager import GnosisManager
    from rotkehlchen.chain.optimism.manager import OptimismManager
    from rotkehlchen.chain.polygon_pos.manager import PolygonPOSManager
    from rotkehlchen.chain.scroll.manager import ScrollManager
    from rotkehlchen.chain.substrate.manager import SubstrateManager
    from rotkehlchen.chain.zksync_lite.manager import ZksyncLiteManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.externalapis.beaconchain.service import BeaconChain

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _module_name_to_class(module_name: ModuleName) -> type[EthereumModule]:
    class_name = ''.join(word.title() for word in module_name.split('_'))
    extra_path = MODULE_NAME_TO_PATH.get(module_name)
    search_path = 'rotkehlchen.chain.ethereum.modules'
    if extra_path is not None:
        search_path += extra_path

    try:
        module = import_module(search_path)
    except ModuleNotFoundError as e:
        raise AssertionError(f'Could not find {search_path} in ethereum modules') from e
    # else

    klass = getattr(module, class_name, None)
    assert klass, f'Could not find object {class_name} in {search_path}'
    return klass


# Mapping to token symbols to ignore. True means all
DEFI_PROTOCOLS_TO_SKIP_ASSETS = {
    # aTokens are already detected at token balance queries
    'Aave': True,  # True means all
    'Aave V2': True,  # True means all
    # stkAAVE and staking incentives are already detected
    'Aave • Staking': True,
    # cTokens are already detected at token balance queries
    'Compound': True,  # True means all
    # Curve balances are detected by our scan for ERC20 tokens
    'Curve': True,  # True means all
    # Curve gauges balances are now being detected separately by us
    'Curve • Liquidity Gauges': True,  # True means all
    # Chai is a normal token we query
    'Chai': True,  # True means all
    # Chitoken is a normal token we query
    'Chi Gastoken by 1inch': True,  # True means all
    # yearn vault balances are detected by the yTokens
    'yearn.finance • Vaults': True,  # True means all
    'Yearn Token Vaults': True,
    # Synthetix SNX token is in our packaged DB
    'Synthetix': ['SNX'],
    # Ampleforth's AMPL token is in our packaged DB
    'Ampleforth': ['AMPL'],
    # MakerDao vault balances are already detected by our code.
    # Note that DeFi SDK only detects them for the proxies.
    'Multi-Collateral Dai': True,  # True means all
    # We already got some pie dao tokens in the packaged DB
    'PieDAO': ['BCP', 'BTC++', 'DEFI++', 'DEFI+S', 'DEFI+L', 'YPIE'],
    'Dai Savings Rate': True,
}
DEFI_PROTOCOLS_TO_SKIP_LIABILITIES = {
    'Multi-Collateral Dai': True,  # True means all
    'Aave': True,
    'Aave V2': True,
    'Compound': True,
}
CHAIN_TO_BALANCE_PROTOCOLS = {
    ChainID.ETHEREUM: (
        Compoundv3Balances,
        CurveBalances,  # only needed in ethereum, because other chains have new gauge contracts
        ConvexBalances,
        ThegraphBalances,
        OctantBalances,
        EigenlayerBalances,
        HedgeyBalances,
        BlurBalances,
        GearboxBalances,
        SafeBalances,
        AaveBalances,
        CurveLendBalances,
        UniswapV3Balances,
        PendleBalances,
        CurveCrvusdBalances,
    ),
    ChainID.OPTIMISM: (
        VelodromeBalances,
        Compoundv3Balances,
        HopBalances,
        GearboxBalancesOptimism,
        ExtrafiBalancesOp,
        WalletconnectBalances,
        CurveLendBalances,
        GivethOptimismBalances,
        UniswapV3Balances,
    ),
    ChainID.BASE: (
        Compoundv3Balances,
        AerodromeBalances,
        HopBalances,
        ExtrafiBalancesBase,
        UniswapV3Balances,
    ),
    ChainID.ARBITRUM_ONE: (
        Compoundv3Balances,
        GmxBalances,
        ThegraphBalancesArbitrumOne,
        HopBalances,
        GearboxBalancesArbitrumOne,
        UmamiBalances,
        CurveLendBalances,
        UniswapV3Balances,
        HyperliquidBalances,
    ),
    ChainID.POLYGON_POS: (
        Compoundv3Balances,
        HopBalances,
        UniswapV3Balances,
    ),
    ChainID.GNOSIS: (
        HopBalances,
        GivethGnosisBalances,
    ),
    ChainID.SCROLL: (Compoundv3Balances,),
    ChainID.BINANCE_SC: (UniswapV3Balances,),
}


T = TypeVar('T')


class ChainsAggregator(CacheableMixIn, LockableQueryMixIn):

    def __init__(
            self,
            blockchain_accounts: BlockchainAccounts,
            ethereum_manager: 'EthereumManager',
            optimism_manager: 'OptimismManager',
            polygon_pos_manager: 'PolygonPOSManager',
            arbitrum_one_manager: 'ArbitrumOneManager',
            base_manager: 'BaseManager',
            gnosis_manager: 'GnosisManager',
            scroll_manager: 'ScrollManager',
            binance_sc_manager: 'BinanceSCManager',
            kusama_manager: 'SubstrateManager',
            polkadot_manager: 'SubstrateManager',
            avalanche_manager: 'AvalancheManager',
            zksync_lite_manager: 'ZksyncLiteManager',
            bitcoin_manager: 'BitcoinManager',
            bitcoin_cash_manager: 'BitcoinCashManager',
            msg_aggregator: MessagesAggregator,
            database: 'DBHandler',
            greenlet_manager: GreenletManager,
            premium: Premium | None,
            data_directory: Path,
            beaconchain: 'BeaconChain',
            btc_derivation_gap_limit: int,
            eth_modules: Sequence[ModuleName],
    ):
        log.debug('Initializing ChainsAggregator')
        super().__init__()
        self.ethereum = ethereum_manager
        self.optimism = optimism_manager
        self.polygon_pos = polygon_pos_manager
        self.arbitrum_one = arbitrum_one_manager
        self.base = base_manager
        self.gnosis = gnosis_manager
        self.scroll = scroll_manager
        self.binance_sc = binance_sc_manager
        self.kusama = kusama_manager
        self.polkadot = polkadot_manager
        self.avalanche = avalanche_manager
        self.zksync_lite = zksync_lite_manager
        self.bitcoin = bitcoin_manager
        self.bitcoin_cash = bitcoin_cash_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.accounts = blockchain_accounts
        self.data_directory = data_directory
        self.beaconchain = beaconchain
        self.btc_derivation_gap_limit = btc_derivation_gap_limit

        # All of these locks are used, but the chain ones with dynamic getattr below
        self.defi_lock = Semaphore()
        self.btc_lock = Semaphore()
        self.bch_lock = Semaphore()
        self.eth_lock = Semaphore()
        self.ksm_lock = Semaphore()
        self.dot_lock = Semaphore()
        self.avax_lock = Semaphore()
        self.optimism_lock = Semaphore()
        self.polygon_pos_lock = Semaphore()
        self.arbitrum_one_lock = Semaphore()
        self.base_lock = Semaphore()
        self.gnosis_lock = Semaphore()
        self.scroll_lock = Semaphore()
        self.binance_sc_lock = Semaphore()
        self.zksync_lite_lock = Semaphore()

        # Per account balances
        self.balances = BlockchainBalances(db=database)
        # Per asset total balances
        self.totals: BalanceSheet = BalanceSheet()
        self.premium = premium
        self.greenlet_manager = greenlet_manager
        self.eth_modules: dict[ModuleName, EthereumModule] = {}
        for given_module in eth_modules:
            self.activate_module(given_module)

        self.eth_asset = A_ETH.resolve_to_crypto_asset()
        # type ignores here are to keep the callable mappings generic enough
        self.chain_modify_init: dict[SupportedBlockchain, Callable[[SupportedBlockchain, Literal['append', 'remove']], None]] = {  # noqa: E501
            SupportedBlockchain.KUSAMA: self._init_substrate_account_modification,  # type:ignore
            SupportedBlockchain.POLKADOT: self._init_substrate_account_modification,  # type:ignore
        }
        self.chain_modify_append: dict[SupportedBlockchain, Callable[[SupportedBlockchain, BlockchainAddress], None]] = {  # noqa: E501
            SupportedBlockchain.ETHEREUM: self._append_eth_account_modification,  # type:ignore
        }
        self.chain_modify_remove: dict[SupportedBlockchain, Callable[[SupportedBlockchain, BlockchainAddress], None]] = {  # noqa: E501
            SupportedBlockchain.ETHEREUM: self._remove_eth_account_modification,  # type:ignore
        }

    def __del__(self) -> None:
        del self.ethereum

    def set_ksm_rpc_endpoint(self, endpoint: str) -> tuple[bool, str]:
        return self.kusama.set_rpc_endpoint(endpoint)

    def set_dot_rpc_endpoint(self, endpoint: str) -> tuple[bool, str]:
        return self.polkadot.set_rpc_endpoint(endpoint)

    def activate_premium_status(self, premium: Premium) -> None:
        self.premium = premium
        for _, module in self.iterate_modules():
            if hasattr(module, 'premium') is True:
                module.premium = premium  # type: ignore

    def deactivate_premium_status(self) -> None:
        self.premium = None
        for _, module in self.iterate_modules():
            if hasattr(module, 'premium') is True and module.premium is not None:  # type: ignore
                module.premium = None  # type: ignore

        # Also flush the cache of anything that is touched by eth2 validators since
        # without premium we have a limit
        self.flush_cache('query_eth2_balances')
        self.flush_cache('query_balances')
        self.flush_cache('query_balances', blockchain=SupportedBlockchain.ETHEREUM_BEACONCHAIN)
        self.flush_cache('query_balances', blockchain=None, ignore_cache=False)
        self.flush_cache('query_balances', blockchain=SupportedBlockchain.ETHEREUM_BEACONCHAIN, ignore_cache=False)  # noqa: E501

    def process_new_modules_list(self, module_names: list[ModuleName]) -> None:
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

    def iterate_modules(self) -> Iterator[tuple[str, EthereumModule]]:
        yield from self.eth_modules.items()

    def queried_addresses_for_module(self, module: ModuleName) -> tuple[ChecksumEvmAddress, ...]:
        """Returns the addresses to query for the given module/protocol"""
        with self.database.conn.read_ctx() as cursor:
            result = QueriedAddresses(self.database).get_queried_addresses_for_module(cursor, module)  # noqa: E501
        return result if result is not None else self.accounts.eth

    def activate_module(self, module_name: ModuleName) -> EthereumModule | None:
        """Activates an ethereum module by module name"""
        module = self.eth_modules.get(module_name, None)
        if module:
            return module  # already activated

        log.debug(f'Activating {module_name} module')
        kwargs: dict[str, Any] = {}
        if module_name == 'eth2':
            with self.database.conn.read_ctx() as cursor:
                kwargs['beacon_rpc_endpoint'] = self.database.get_setting(cursor, 'beacon_rpc_endpoint')  # noqa: E501
            kwargs['beaconchain'] = self.beaconchain
        klass = _module_name_to_class(module_name)
        try:
            instance = klass(
                ethereum_inquirer=self.ethereum.node_inquirer,
                database=self.database,
                premium=self.premium,
                msg_aggregator=self.msg_aggregator,
                **kwargs,
            )
        except (ModuleInitializationFailure, UnknownAsset, WrongAssetType) as e:
            self.msg_aggregator.add_error(f'Failed to activate {module_name} due to: {e!s}')
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
    def get_module(self, module_name: Literal['eth2']) -> 'Eth2 | None':
        ...

    @overload
    def get_module(self, module_name: Literal['loopring']) -> 'Loopring | None':
        ...

    @overload
    def get_module(self, module_name: Literal['makerdao_dsr']) -> 'MakerdaoDsr | None':
        ...

    @overload
    def get_module(self, module_name: Literal['makerdao_vaults']) -> 'MakerdaoVaults | None':
        ...

    @overload
    def get_module(self, module_name: Literal['uniswap']) -> 'Uniswap | None':
        ...

    @overload
    def get_module(self, module_name: Literal['sushiswap']) -> 'Sushiswap | None':
        ...

    @overload
    def get_module(self, module_name: Literal['liquity']) -> 'Liquity | None':
        ...

    @overload
    def get_module(self, module_name: Literal['pickle_finance']) -> 'PickleFinance | None':
        ...

    @overload
    def get_module(self, module_name: Literal['nfts']) -> 'Nfts | None':
        ...

    def get_module(self, module_name: ModuleName) -> Any | None:
        instance = self.eth_modules.get(module_name, None)
        if instance is None:  # not activated
            return None

        return instance

    def get_balances_update(self, chain: SupportedBlockchain | None) -> BlockchainBalancesUpdate:
        """Returns a balances update to be consumed by the API."""
        return BlockchainBalancesUpdate(
            given_chain=chain,
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
        forced_bch_legacy_addresses = set()
        if (append_bch_case := blockchain == SupportedBlockchain.BITCOIN_CASH and append_or_remove == 'append'):  # noqa: E501
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
            if append_bch_case:
                # an already existing bch address can be added but in a different format
                # so convert all bch addresses to the same format and compare.
                existent = account in self.accounts.bch or force_address_to_legacy_address(account) in forced_bch_legacy_addresses  # noqa: E501
            else:
                existent = account in self.accounts.get(blockchain)

            if (
                    (existent is True and append_or_remove == 'append') or
                    (existent is False and append_or_remove == 'remove')
            ):
                bad_accounts.append(account)

        if len(bad_accounts) != 0:
            word = 'already' if append_or_remove == 'append' else "don't"
            raise InputError(
                f'Blockchain account/s {",".join(bad_accounts)} {word} exist',
            )

    @protect_with_lock(arguments_matter=True)
    @cache_response_timewise(forward_ignore_cache=True)
    def query_balances(
            self,
            blockchain: SupportedBlockchain | None = None,
            ignore_cache: bool = False,
    ) -> BlockchainBalancesUpdate:
        """Queries either all, or specific blockchain balances

        If querying beaconchain and ignore_cache is true then each eth1 address is also
        checked for the validators it has deposited and the deposits are fetched.

        May raise:
        - RemoteError if an external service such as Etherscan or blockchain.info
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        xpub_manager = XpubManager(chains_aggregator=self)
        if blockchain is not None:
            query_method = f'query_{blockchain.get_key()}_balances'
            getattr(self, query_method)(ignore_cache=ignore_cache)
            if ignore_cache is True and blockchain.is_bitcoin():
                xpub_manager.check_for_new_xpub_addresses(blockchain=blockchain)  # type: ignore # is checked in the if
        else:  # all chains
            for chain in SupportedBlockchain:
                if chain.is_evm() and len(self.accounts.get(chain)) == 0:  # don't check eth2 and bitcoin since we might need to query new addresses  # noqa: E501
                    continue

                query_method = f'query_{chain.get_key()}_balances'
                getattr(self, query_method)(ignore_cache=ignore_cache)
                if ignore_cache is True and chain.is_bitcoin():
                    xpub_manager.check_for_new_xpub_addresses(blockchain=chain)  # type: ignore # is checked in the if

        self.totals = self.balances.recalculate_totals()
        return self.get_balances_update(blockchain)

    @protect_with_lock()
    @cache_response_timewise()
    def query_btc_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """Queries bitcoin block explorer APIs for the balance of all BTC accounts

        May raise:
        - RemoteError if there is a problem querying any remote
        """
        if len(self.accounts.btc) == 0:
            return

        self.balances.btc = {}
        btc_usd_price = Inquirer.find_usd_price(A_BTC)
        balances = self.bitcoin.get_balances(self.accounts.btc)
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
        """Queries bch block explorer APIs for the balance of all BCH accounts

        May raise:
        - RemoteError if there is a problem querying any remote
        """
        if len(self.accounts.bch) == 0:
            return

        self.balances.bch = {}
        bch_usd_price = Inquirer.find_usd_price(A_BCH)
        balances = self.bitcoin_cash.get_balances(self.accounts.bch)
        for account, balance in balances.items():
            self.balances.bch[account] = Balance(
                amount=balance,
                usd_value=balance * bch_usd_price,
            )

    @protect_with_lock()
    @cache_response_timewise()
    def query_ksm_balances(
            self,  # pylint: disable=unused-argument
            wait_available_node: bool = True,
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """Queries the KSM balances of the accounts via Kusama endpoints.

        May raise:
        - RemoteError: if no nodes are available or the balances request fails.
        """
        if len(self.accounts.ksm) == 0:
            return

        ksm_usd_price = Inquirer.find_usd_price(A_KSM)
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
            self.balances.ksm[account] = BalanceSheet()
            self.balances.ksm[account].assets[A_KSM][DEFAULT_BALANCE_LABEL] = balance

    @protect_with_lock()
    @cache_response_timewise()
    def query_avax_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """Queries the AVAX balances of the accounts via Avalanche rpcs.
        May raise:
        - RemoteError: if no nodes are available or the balances request fails.
        """
        if len(self.accounts.avax) == 0:
            return

        # Query avax balance
        avax_usd_price = Inquirer.find_usd_price(A_AVAX)
        account_amount = self.avalanche.get_multiavax_balance(self.accounts.avax)
        for account, amount in account_amount.items():
            usd_value = amount * avax_usd_price
            self.balances.avax[account] = BalanceSheet()
            self.balances.avax[account].assets[A_AVAX][DEFAULT_BALANCE_LABEL] = Balance(amount, usd_value)  # noqa: E501

    @protect_with_lock()
    @cache_response_timewise()
    def query_dot_balances(
            self,  # pylint: disable=unused-argument
            wait_available_node: bool = True,
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """Queries the DOT balances of the accounts via Polkadot endpoints.

        May raise:
        - RemoteError: if no nodes are available or the balances request fails.
        """
        if len(self.accounts.dot) == 0:
            return

        dot_usd_price = Inquirer.find_usd_price(A_DOT)
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
            self.balances.dot[account] = BalanceSheet()
            self.balances.dot[account].assets[A_DOT][DEFAULT_BALANCE_LABEL] = balance

    @protect_with_lock()
    @cache_response_timewise()
    def query_zksync_lite_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """Queries the balance of the zksync lite chain.

        May raise:
        - RemoteError: if no nodes are available or the balances request fails.
        """
        if len(self.accounts.zksync_lite) == 0:
            return

        balances = self.zksync_lite.get_balances(self.accounts.zksync_lite)
        for address, asset_balances in balances.items():
            for asset, balance in asset_balances.items():
                self.balances.zksync_lite[address].assets[asset][DEFAULT_BALANCE_LABEL] = balance

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
            blockchain.get_key(),
        )
        accounts_to_remove = [x for x in getattr(self.accounts, blockchain.get_key()) if x not in db_btc_accounts]  # noqa: E501
        self.modify_blockchain_accounts(
            blockchain=blockchain,
            accounts=accounts_to_remove,
            append_or_remove='remove',
        )

    def remove_single_blockchain_accounts(
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

    def _init_substrate_account_modification(
            self,
            blockchain: SUPPORTED_SUBSTRATE_CHAINS,
            append_or_remove: Literal['append', 'remove'],
    ) -> None:
        """Extra code to run when substrate account modification start"""
        if append_or_remove != 'append':
            return  # we only care about appending

        substrate_manager: SubstrateManager = getattr(self, blockchain.name.lower())
        # When adding account for the first time we should connect to the nodes
        if len(substrate_manager.available_nodes_call_order) == 0:
            substrate_manager.attempt_connections()
            wait_until_a_node_is_available(
                substrate_manager=substrate_manager,
                seconds=SUBSTRATE_NODE_CONNECTION_TIMEOUT,
            )

    def _append_eth_account_modification(
            self,
            blockchain: Literal[SupportedBlockchain.ETHEREUM],  # pylint: disable=unused-argument
            address: ChecksumEvmAddress,
    ) -> None:
        """Extra code to run when eth account addition happens"""
        if blockchain == SupportedBlockchain.ETHEREUM:  # add it first so that it's there for module's on account addition  # noqa: E501
            self.ethereum.node_inquirer.proxies_inquirer.query_address_for_proxies(address)
        for _, module in self.iterate_modules():
            module.on_account_addition(address)

    def _remove_eth_account_modification(
            self,
            blockchain: Literal[SupportedBlockchain.ETHEREUM],  # pylint: disable=unused-argument
            address: ChecksumEvmAddress,
    ) -> None:
        """Extra code to run when eth account removal happens"""
        if blockchain == SupportedBlockchain.ETHEREUM:
            self.ethereum.node_inquirer.proxies_inquirer.reset_last_query_ts()

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
        - InputError if any of the accounts exist while trying to append or any of the
        accounts doesn't exist while trying to remove
        - RemoteError if there is a problem querying an external service such
        as etherscan or blockchain.info or couldn't connect to a node (for polkadot and kusama)
        """
        self.check_accounts_existence(
            blockchain=blockchain,
            accounts=accounts,
            append_or_remove=append_or_remove,
        )
        chain_key = blockchain.get_key()
        lock = getattr(self, f'{chain_key}_lock')
        balances = self.balances.get(chain=blockchain)
        with lock:
            self.flush_cache(f'query_{chain_key}_balances')
            chain_modify_init = self.chain_modify_init.get(blockchain)
            if chain_modify_init is not None:
                chain_modify_init(blockchain, append_or_remove)
            for account in accounts:
                if append_or_remove == 'append':
                    self.accounts.add(blockchain=blockchain, address=account)
                    chain_modify_append = self.chain_modify_append.get(blockchain)
                    if chain_modify_append is not None:
                        chain_modify_append(blockchain, account)
                else:  # remove
                    balances.pop(account, None)  # type: ignore  # mypy can't understand each account has same type
                    self.accounts.remove(blockchain=blockchain, address=account)
                    chain_modify_remove = self.chain_modify_remove.get(blockchain)
                    if chain_modify_remove is not None:
                        chain_modify_remove(blockchain, account)

        # we are adding/removing accounts, make sure query cache is flushed
        self.flush_cache('query_balances')
        self.flush_cache('query_balances', blockchain=blockchain)
        self.flush_cache('query_balances', blockchain=None, ignore_cache=False)
        self.flush_cache('query_balances', blockchain=blockchain, ignore_cache=False)
        self.flush_cache(f'query_{chain_key}_balances')

        # recalculate totals
        if append_or_remove == 'remove':  # at addition no balances are queried so no need
            self.totals = self.balances.recalculate_totals()

    @protect_with_lock()
    @cache_response_timewise(forward_ignore_cache=True)
    def query_eth2_balances(
            self,
            ignore_cache: bool,
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
            fetch_validators_for_eth1=ignore_cache,
        )
        for pubkey, balance in balance_mapping.items():
            self.balances.eth2[pubkey] = BalanceSheet()
            self.balances.eth2[pubkey].assets[A_ETH2][DEFAULT_BALANCE_LABEL] = balance

    @staticmethod
    def _update_balances_after_token_query(
            dsr_proxy_append: bool,
            balance_result: dict[ChecksumEvmAddress, dict[EvmToken, FVal]],
            token_usd_price: dict[EvmToken, Price],
            balances: defaultdict[ChecksumEvmAddress, BalanceSheet],
            balance_label: Literal['address', 'makerdao vault'] = DEFAULT_BALANCE_LABEL,
    ) -> None:
        # Update the per account token balance and usd value
        for account, token_balances in balance_result.items():
            for token, token_balance in token_balances.items():
                balance = Balance(
                    amount=token_balance,
                    usd_value=token_balance * token_usd_price[token],
                )
                protocol = token.protocol or balance_label
                assets_or_liabilities = balances[account].liabilities if token.is_liability() else balances[account].assets  # noqa: E501
                if dsr_proxy_append:
                    assets_or_liabilities[token][protocol] += balance
                else:
                    assets_or_liabilities[token][protocol] = balance

    def query_evm_tokens(
            self,
            manager: 'EvmManager',
            balances: defaultdict[ChecksumEvmAddress, BalanceSheet],
    ) -> None:
        """Queries evm token balance via either etherscan or evm node

        Should come here during addition of a new account or querying of all token
        balances.

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        try:
            balance_result, token_usd_price = manager.tokens.query_tokens_for_addresses(
                addresses=self.accounts.get(manager.node_inquirer.blockchain),
            )
        except BadFunctionCallOutput as e:
            log.error(
                f'Assuming unsynced chain. Got web3 BadFunctionCallOutput '
                f'exception: {e!s}',
            )
            raise EthSyncError(
                f'Tried to use the {manager.node_inquirer.blockchain!s} chain of the provided '
                'client to query token balances but the chain is not synced.',
            ) from e

        self._update_balances_after_token_query(
            dsr_proxy_append=False,
            balance_result=balance_result,
            token_usd_price=token_usd_price,
            balances=balances,
        )

    def query_evm_chain_balances(self, chain: SUPPORTED_EVM_CHAINS_TYPE) -> None:
        """Queries all the balances for an evm chain and populates the state

        May raise:
        - RemoteError if an external service such as Etherscan or cryptocompare
        is queried and there is a problem with its query.
        - EthSyncError if querying the token balances through a provided ethereum
        client and the chain is not synced
        """
        accounts = self.accounts.get(chain)
        if len(accounts) == 0:
            return

        # Clear existing balances for this chain to avoid accumulation
        chain_balances = self.balances.get(chain)
        for account in accounts:
            chain_balances[account] = BalanceSheet()

        # Query native token balances
        manager = cast('EvmManager', self.get_chain_manager(chain))
        native_token_usd_price = Inquirer.find_usd_price(manager.node_inquirer.native_token)
        chain_balances = self.balances.get(chain)
        for account, balance in manager.node_inquirer.get_multi_balance(accounts).items():
            if balance != ZERO:  # accounts (e.g. multisigs) can have zero balances
                chain_balances[account].assets[manager.node_inquirer.native_token][DEFAULT_BALANCE_LABEL] = Balance(  # noqa: E501
                    amount=balance,
                    usd_value=balance * native_token_usd_price,
                )
        self.query_evm_tokens(manager=manager, balances=chain_balances)

    @protect_with_lock()
    @cache_response_timewise()
    def query_optimism_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """
        Queries all the optimism balances and populates the state.
        Same potential exceptions as ethereum
        """
        self.query_evm_chain_balances(chain=SupportedBlockchain.OPTIMISM)
        self._query_protocols_with_balance(chain_id=ChainID.OPTIMISM)

    @protect_with_lock()
    @cache_response_timewise()
    def query_polygon_pos_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """
        Queries all the polygon pos balances and populates the state.
        Same potential exceptions as ethereum
        """
        self.query_evm_chain_balances(chain=SupportedBlockchain.POLYGON_POS)
        self._query_protocols_with_balance(chain_id=ChainID.POLYGON_POS)

    @protect_with_lock()
    @cache_response_timewise()
    def query_arbitrum_one_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """
        Queries all the arbitrum one balances and populates the state.
        Same potential exceptions as ethereum
        """
        self.query_evm_chain_balances(chain=SupportedBlockchain.ARBITRUM_ONE)
        self._query_protocols_with_balance(chain_id=ChainID.ARBITRUM_ONE)

    @protect_with_lock()
    @cache_response_timewise()
    def query_base_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """
        Queries all the base balances and populates the state.
        Same potential exceptions as ethereum
        """
        self.query_evm_chain_balances(chain=SupportedBlockchain.BASE)
        self._query_protocols_with_balance(chain_id=ChainID.BASE)

    @protect_with_lock()
    @cache_response_timewise()
    def query_gnosis_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """
        Queries all the gnosis balances and populates the state.
        Same potential exceptions as ethereum
        """
        self.query_evm_chain_balances(chain=SupportedBlockchain.GNOSIS)
        self._query_protocols_with_balance(chain_id=ChainID.GNOSIS)

    @protect_with_lock()
    @cache_response_timewise()
    def query_scroll_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """
        Queries all the scroll balances and populates the state.
        Same potential exceptions as ethereum
        """
        self.query_evm_chain_balances(chain=SupportedBlockchain.SCROLL)
        self._query_protocols_with_balance(chain_id=ChainID.SCROLL)

    @protect_with_lock()
    @cache_response_timewise()
    def query_binance_sc_balances(
            self,  # pylint: disable=unused-argument
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> None:
        """
        Queries all the binance smart chain balances and populates the state.
        Same potential exceptions as ethereum
        """
        self.query_evm_chain_balances(chain=SupportedBlockchain.BINANCE_SC)
        self._query_protocols_with_balance(chain_id=ChainID.BINANCE_SC)

    @protect_with_lock()
    @cache_response_timewise()
    def query_eth_balances(
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
        self.query_evm_chain_balances(chain=SupportedBlockchain.ETHEREUM)
        self._add_eth_protocol_balances(eth_balances=self.balances.eth)
        self._query_protocols_with_balance(chain_id=ChainID.ETHEREUM)

    def _query_protocols_with_balance(self, chain_id: CHAIN_IDS_WITH_BALANCE_PROTOCOLS) -> None:
        """
        Query for balances of protocols in which tokens can be locked without returning a liquid
        version of the locked token. For example staking tokens in an old curve gauge. This balance
        needs to be added to the total balance of the account. Examples of such protocols are
        Legacy Curve gauges in ethereum, Convex and Velodrome.
        """
        chain: SUPPORTED_EVM_CHAINS_TYPE = ChainID.to_blockchain(chain_id)  # type: ignore  # CHAIN_IDS_WITH_BALANCE_PROTOCOLS only contains SUPPORTED_EVM_CHAINS_TYPE
        chain_manager = self.get_evm_manager(chain_id)
        existing_balances: defaultdict[ChecksumEvmAddress, BalanceSheet] = self.balances.get(chain)
        for protocol in CHAIN_TO_BALANCE_PROTOCOLS[chain_id]:
            protocol_with_balance: ProtocolWithBalance = protocol(
                evm_inquirer=chain_manager.node_inquirer,  # type: ignore  # mypy can't match all possibilities here
                tx_decoder=chain_manager.transactions_decoder,  # type: ignore  # mypy can't match all possibilities here
            )
            try:
                protocol_balances = protocol_with_balance.query_balances()
            except RemoteError as e:
                log.error(f'Failed to query balances for {protocol} due to {e}. Skipping')
                continue

            for address, asset_balances in protocol_balances.items():
                existing_balances[address] += asset_balances

    def _add_eth_protocol_balances(self, eth_balances: defaultdict[ChecksumEvmAddress, BalanceSheet]) -> None:  # noqa: E501
        """Also count token balances that may come from various eth protocols"""
        # If we have anything in DSR also count it towards total blockchain balances
        if (dsr_module := self.get_module('makerdao_dsr')) is not None:
            current_dsr_report = dsr_module.get_current_dsr()
            for dsr_account, balance_entry in current_dsr_report.balances.items():

                if balance_entry.amount == ZERO:
                    continue

                eth_balances[dsr_account].assets[A_DAI][CPT_DSR] += balance_entry

        # Also count the vault balances
        if (vaults_module := self.get_module('makerdao_vaults')) is not None:
            vault_balances = vaults_module.get_balances()
            for address, entry in vault_balances.items():
                if address not in eth_balances:
                    self.msg_aggregator.add_error(
                        f'The owner of a vault {address} was not in the tracked addresses.'
                        f' This should not happen and is probably a bug. Please report it.',
                    )
                else:
                    eth_balances[address] += entry

        # If any of the related modules is on (TODO: switch to counting events activity)
        if (liquity_module := self.get_module('liquity')) is not None or vaults_module is not None or dsr_module is not None:  # noqa: E501
            proxy_mappings = self.ethereum.node_inquirer.proxies_inquirer.get_accounts_having_proxy()  # noqa: E501
            for single_proxy_mappings in proxy_mappings.values():
                proxy_to_address = {}
                proxy_addresses = []
                for user_address, proxy_address in single_proxy_mappings.items():
                    proxy_to_address[proxy_address] = user_address
                    proxy_addresses.append(proxy_address)

                evmtokens = self.get_chain_manager(SupportedBlockchain.ETHEREUM).tokens
                try:
                    balance_result, token_usd_price = evmtokens.query_tokens_for_addresses(
                        addresses=proxy_addresses,
                    )
                except BadFunctionCallOutput as e:
                    log.error(
                        f'Assuming unsynced chain. Got web3 BadFunctionCallOutput '
                        f'exception: {e!s}',
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
                    balance_label=CPT_VAULT,
                    balances=eth_balances,
                )

        if (pickle_module := self.get_module('pickle_finance')) is not None:
            pickle_balances_per_address = pickle_module.balances_in_protocol(
                addresses=self.queried_addresses_for_module('pickle_finance'),
            )
            for address, pickle_balances in pickle_balances_per_address.items():
                for asset_balance in pickle_balances:
                    eth_balances[address].assets[asset_balance.asset][CPT_PICKLE] += asset_balance.balance  # noqa: E501

        if liquity_module is not None:
            liquity_addresses = self.queried_addresses_for_module('liquity')
            # Get trove information
            liquity_balances = liquity_module.get_positions(given_addresses=liquity_addresses)
            for address, deposits in liquity_balances['balances'].items():
                if (collateral := deposits.collateral.balance).amount > ZERO:
                    eth_balances[address].assets[A_ETH][CPT_LIQUITY] += collateral
                if (debt := deposits.debt).balance.amount > ZERO:
                    eth_balances[address].liabilities[debt.asset][CPT_LIQUITY] += debt.balance

            # Get staked amounts
            liquity_module.enrich_staking_balances(
                balances=eth_balances,
                queried_addresses=liquity_addresses,
            )

    def get_eth2_daily_stats(
            self,
            filter_query: Eth2DailyStatsFilterQuery,
            only_cache: bool,
    ) -> tuple[list['ValidatorDailyStats'], int, FVal]:
        """May raise:

        - ModuleInactive if eth2 module is not activated.
        - RemoteError if it's fetching data and sources can't be queried.
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant query eth2 daily stats details since eth2 module is not active')  # noqa: E501
        with self.database.conn.read_ctx() as cursor:
            daily_stats, total_found, sum_pnl = eth2.get_validator_daily_stats(
                cursor=cursor,
                filter_query=filter_query,
                only_cache=only_cache,
            )
            return daily_stats, total_found, sum_pnl

    @protect_with_lock()
    @cache_response_timewise()
    def refresh_eth2_get_daily_stats(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> list['ValidatorDailyStats']:
        """Refresh eth2 validator data and get and return the daily stats.

        May raise:
        - ModuleInactive if eth2 module is not activated
        - RemoteError if a remote query to beacon chain fails and is not caught in the method
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant query eth2 history events since eth2 module is not active')

        if to_timestamp < 1607212800:  # Dec 1st 2020 UTC
            return []  # no need to bother querying before beacon chain launch

        eth2.detect_and_refresh_validators(addresses=self.queried_addresses_for_module('eth2'))
        # And now get all daily stats and create defi events for them
        with self.database.conn.read_ctx() as cursor:
            stats, _, _ = eth2.get_validator_daily_stats(
                cursor=cursor,
                filter_query=Eth2DailyStatsFilterQuery.make(from_ts=from_timestamp, to_ts=to_timestamp),  # noqa: E501
                only_cache=False,
            )
            index_to_ownership = DBEth2(self.database).get_index_to_ownership(cursor)

        for stats_entry in stats:
            if stats_entry.pnl == ZERO:
                continue

            # Take into account the validator ownership proportion if is not 100%
            validator_ownership = index_to_ownership.get(stats_entry.validator_index, ONE)
            if validator_ownership != ONE:
                stats_entry.pnl *= validator_ownership
                stats_entry.ownership_percentage = validator_ownership

        return stats

    def get_eth2_validators(
            self,
            ignore_cache: bool,
            validator_indices: set[int] | None,
    ) -> list['ValidatorDetailsWithStatus']:
        """May raise:
        - ModuleInactive if eth2 module is not activated
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant get eth2 validators since the eth2 module is not active')

        return eth2.get_validators(
            ignore_cache=ignore_cache,
            addresses=self.queried_addresses_for_module('eth2'),
            validator_indices=validator_indices,
        )

    def edit_eth2_validator(self, validator_index: int, ownership_proportion: FVal) -> None:
        """Edit a validator to modify its ownership proportion. May raise:
        - ModuleInactive if eth2 module is not active
        - InputError if no row was affected
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant edit eth2 validators since the eth2 module is not active')
        with self.database.user_write() as write_cursor:
            DBEth2(self.database).edit_validator_ownership(
                write_cursor=write_cursor,
                validator_index=validator_index,
                ownership_proportion=ownership_proportion,
            )
        self.flush_cache('get_eth2_daily_stats')
        self.flush_cache('query_eth2_balances')
        self.flush_cache('query_balances')
        self.flush_cache('query_balances', blockchain=SupportedBlockchain.ETHEREUM_BEACONCHAIN)
        self.flush_cache('query_balances', blockchain=None, ignore_cache=False)
        self.flush_cache('query_balances', blockchain=SupportedBlockchain.ETHEREUM_BEACONCHAIN, ignore_cache=False)  # noqa: E501

    def add_eth2_validator(
            self,
            validator_index: int | None,
            public_key: Eth2PubKey | None,
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
        eth2.add_validator(
            validator_index=validator_index,
            public_key=public_key,
            ownership_proportion=ownership_proportion,
        )
        self.flush_eth2_cache()

    def delete_eth2_validators(self, validator_indices: list[int]) -> None:
        """May raise:
        - ModuleInactive if eth2 module is not activated
        - InputError if the validator is not found in the DB
        """
        eth2 = self.get_module('eth2')
        if eth2 is None:
            raise ModuleInactive('Cant delete eth2 validator since eth2 module is not active')

        DBEth2(self.database).delete_validators(validator_indices)
        self.flush_eth2_cache()

    @cache_response_timewise()
    def get_loopring_balances(self) -> dict[CryptoAsset, Balance]:
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
        aggregated_balances: dict[CryptoAsset, Balance] = defaultdict(Balance)
        for assets in balances.values():
            for asset, balance in assets.items():
                aggregated_balances[asset] += balance

        return dict(aggregated_balances)

    def get_chain_manager(
            self,
            blockchain: CHAINS_WITH_CHAIN_MANAGER,
    ) -> Any:
        """Returns blockchain manager"""
        attr = blockchain.name.lower()
        return getattr(self, attr)

    def get_evm_manager(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> 'EvmManager':  # type ignore below due to inability to understand limitation
        return self.get_chain_manager(chain_id.to_blockchain())  # type: ignore[arg-type]

    def is_safe_proxy_or_eoa(
            self,
            address: ChecksumEvmAddress,
            chain: SUPPORTED_EVM_CHAINS_TYPE,
    ) -> bool:
        """
        Check if an address is a SAFE contract or an EoA. We do this by checking the getThreshold,
        VERSION and getChainId methods. We assume that if a contract has the same methods as a
        safe then it is a safe. Also EoAs return (true, b'') for any method so this function
        will also return True.
        """
        if chain in (SupportedBlockchain.ZKSYNC_LITE, SupportedBlockchain.AVALANCHE):
            # We don't support those chains as the others so consider them addresses.
            return True

        manager: EvmNodeInquirer = self.get_chain_manager(chain).node_inquirer
        contract = Web3().eth.contract(address=address, abi=SAFE_BASIC_ABI)
        calls = [
            (address, contract.encode_abi(method_name))
            for method_name in ('getThreshold', 'VERSION', 'getChainId')
        ]
        try:
            outputs = manager.multicall_2(
                calls=calls,
                require_success=False,
            )
        except RemoteError as e:
            log.error(
                f'Failed to check SAFE properties for {address} in {chain} due to {e}. Skipping',
            )
            return False

        return all(result_tuple[0] for result_tuple in outputs)

    def check_single_address_activity(
            self,
            address: ChecksumEvmAddress,
            chains: list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE],
    ) -> tuple[list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE], list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE]]:
        """Checks whether address is active in the given chains.
        Returns a list of active chains and a list of chains where we couldn't query info
        """
        active_chains = []
        failed_to_query_chains: list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE] = []
        for chain in chains:
            chain_manager: EvmManager = self.get_chain_manager(chain)
            try:
                if chain == SupportedBlockchain.AVALANCHE:
                    avax_manager = cast('AvalancheManager', chain_manager)
                    try:
                        # just check balance and nonce in avalanche
                        has_activity = (
                            avax_manager.w3.eth.get_transaction_count(address) != 0 or
                            avax_manager.get_avax_balance(address) != ZERO
                        )
                    except (requests.exceptions.RequestException, Web3Exception) as e:
                        log.error(f'Failed to check {address} activity in avalanche due to {e!s}')
                        failed_to_query_chains.append(chain)
                        has_activity = False

                    if has_activity is False:
                        continue

                elif chain == SupportedBlockchain.ZKSYNC_LITE:
                    options = {'from': 'latest', 'limit': 1, 'direction': 'older'}
                    try:
                        response = self.zksync_lite._query_api(
                            url=f'accounts/{address}/transactions',
                            options=options,
                        )
                    except RemoteError:
                        failed_to_query_chains.append(chain)
                        continue
                    else:
                        result = response.get('list', None)
                        if not result:  # falsy -> None or no transactions:
                            continue  # do not add the address for the chain

                else:
                    if (blockscout := chain_manager.node_inquirer.blockscout) is not None:
                        try:
                            chain_activity = blockscout.has_activity(address)
                        except RemoteError as e:
                            log.debug(
                                'Failed to check activity using blockscout '
                                f'for {chain} due to {e}',
                            )
                            chain_activity = chain_manager.node_inquirer.etherscan.has_activity(
                                chain_id=chain.to_chain_id(),
                                account=address,
                            )
                    else:
                        chain_activity = chain_manager.node_inquirer.etherscan.has_activity(
                            chain_id=chain.to_chain_id(),
                            account=address,
                        )

                    only_token_spam = (
                        chain_activity == HasChainActivity.TOKENS and
                        chain_manager.transactions.address_has_been_spammed(address=address)
                    )
                    if only_token_spam or chain_activity == HasChainActivity.NONE:
                        continue  # do not add the address for the chain
            except RemoteError as e:
                log.error(f'{e!s} when checking if {address} is active at {chain}')
                failed_to_query_chains.append(chain)
                continue

            active_chains.append(chain)

        return active_chains, failed_to_query_chains

    def track_evm_address(
            self,
            address: ChecksumEvmAddress,
            chains: list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE],
    ) -> tuple[list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE], list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE]]:
        """
        Track address for the chains provided. If the address is already tracked on a
        chain, skips this chain.
        Returns a list of chains where the address was added successfully and a list where we
        failed to check or add it.
        """
        added_chains, failed_chains = [], []
        for chain in chains:
            try:
                self.modify_blockchain_accounts(
                    blockchain=chain,
                    accounts=[address],
                    append_or_remove='append',
                )
            except InputError:
                log.debug(f'Not adding {address} to {chain} since it already exists')
                failed_chains.append(chain)
                continue
            except RemoteError as e:
                log.error(f'Not adding {address} to {chain} due to {e!s}')
                failed_chains.append(chain)
                continue

            added_chains.append(chain)

        return added_chains, failed_chains

    def check_chains_and_add_accounts(
            self,
            account: ChecksumEvmAddress,
            chains: list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE],
    ) -> tuple[
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
        bool,
    ]:
        """
        Accepts an account and a list of chains to check activity in. For each chain checks whether
        the account is active there and if it is, starts tracking it. Returns a tuple of:
        - a list of tuples (chain, account) for each chain where the account was added
        - a list of tuples (chain, account) for each chain where we failed to check the account
        - boolean being False if the account didn't have activity in any chain
        """
        active_chains, failed_to_query_chains = self.check_single_address_activity(
            address=account,
            chains=chains,
        )
        if len(active_chains) == 0:
            return [], [], False

        new_tracked_chains, new_failed_chains = self.track_evm_address(account, active_chains)
        failed_to_query_chains += new_failed_chains
        if len(new_tracked_chains) > 0:
            DBAddressbook(self.database).maybe_make_entry_name_multichain(address=account)

        return (
            [(chain, account) for chain in new_tracked_chains],
            [(chain, account) for chain in failed_to_query_chains],
            True,
        )

    def add_accounts_to_all_evm(
            self,
            accounts: list[ChecksumEvmAddress],
    ) -> tuple[
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
        list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]],
    ]:
        """Adds each account for all evm chain if it is not a contract in ethereum mainnet.

        Returns four lists:
        - list address, chain tuples for all newly added addresses.
        - list address, chain tuples for all addresses already tracked.
        - list address, chain tuples for all addresses that failed to be added.
        - list address, chain tuples for all addresses that have no activity in their chain.
        - list address, chain tuples for all addresses that are contracts except those
        identified as SAFE contracts.

        May raise:
        - RemoteError if an external service such as etherscan is queried and there
        is a problem with its query.
        """
        added_accounts: list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]] = []
        failed_accounts: list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]] = []
        existed_accounts: list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]] = []
        no_activity_accounts: list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]] = []  # noqa: E501
        evm_contract_addresses: list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]] = []  # noqa: E501

        for account in accounts:
            existed_accounts += [(chain, account) for chain in SUPPORTED_EVM_EVMLIKE_CHAINS if account in self.accounts.get(chain)]  # noqa: E501
            # Distinguish between contracts and EOAs
            chains_to_check = [x for x in SUPPORTED_EVM_EVMLIKE_CHAINS if account not in self.accounts.get(x)]  # noqa: E501
            chains_with_valid_addresses = []
            for chain in chains_to_check:
                if self.is_safe_proxy_or_eoa(address=account, chain=chain):  # type: ignore  # the chain is a supportedblockchain here
                    chains_with_valid_addresses.append(chain)
                else:
                    evm_contract_addresses.append((chain, account))

            new_accounts, new_failed_accounts, had_activity = self.check_chains_and_add_accounts(
                account=account,
                chains=chains_with_valid_addresses,
            )

            if had_activity is True:
                added_accounts += new_accounts
                failed_accounts += new_failed_accounts
            elif had_activity is False and len(chains_with_valid_addresses) != 0:
                no_activity_accounts += [(chain, account) for chain in chains_with_valid_addresses]

        return (
            added_accounts,
            existed_accounts,
            failed_accounts,
            no_activity_accounts,
            evm_contract_addresses,
        )

    def detect_evm_accounts(
            self,
            progress_handler: Optional['ProgressUpdater'] = None,
            chains: list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE] | None = None,
    ) -> list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]]:
        """
        Detects user's EVM accounts on different chains and adds them to the tracked accounts.
        If chains is given then detection only happens for those given chains.
        Otherwise for all evm chains.

        1. Iterates through already added addresses
        2. For each address verify that is an EOA or a safe and check which chains it's already in
        3. Get the rest of the chains, and check activity. If active in any of them it tracks the
        address for that chain.

        Returns a list of tuples of (chain, address) for the freshly detected accounts.
        """
        current_accounts: dict[ChecksumEvmAddress, list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE]] = defaultdict(list)  # noqa: E501
        chain: SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE
        for chain in SUPPORTED_EVM_EVMLIKE_CHAINS:
            chain_accounts = self.accounts.get(chain)
            for account in chain_accounts:
                current_accounts[account].append(chain)

        all_evm_chains = set(SUPPORTED_EVM_EVMLIKE_CHAINS) if chains is None else set(chains)
        added_accounts: list[tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ChecksumEvmAddress]] = []
        for account, account_chains in current_accounts.items():
            if progress_handler is not None:
                progress_handler.new_step(f'Checking {account} EVM chain activity')

            chains_to_check = list(all_evm_chains - set(account_chains))
            for chain in list(chains_to_check):
                if not self.is_safe_proxy_or_eoa(address=account, chain=chain):  # type: ignore  # the chain is a supportedblockchain here
                    chains_to_check.remove(chain)

            if len(chains_to_check) == 0:
                continue

            new_added_accounts, _, _ = self.check_chains_and_add_accounts(
                account=account,
                chains=chains_to_check,
            )
            added_accounts += new_added_accounts

        if progress_handler is not None:
            progress_handler.new_step('Potentially write migrated addresses to the DB')

        with self.database.user_write() as write_cursor:
            self.database.add_blockchain_accounts(
                write_cursor=write_cursor,
                account_data=[BlockchainAccountData(chain=chain, address=address) for chain, address in added_accounts],  # noqa: E501
            )

        self.msg_aggregator.add_message(
            message_type=WSMessageType.EVMLIKE_ACCOUNTS_DETECTION,
            data=[
                {'chain': chain.serialize(), 'address': address}
                for chain, address in added_accounts
            ],
        )

        with self.database.user_write() as cursor:
            cursor.execute(  # remember last time evm addresses were detected
                'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                (DBCacheStatic.LAST_EVM_ACCOUNTS_DETECT_TS.value, str(ts_now())),
            )

        return added_accounts

    def iterate_evm_chain_managers(self) -> Iterator['EvmManager']:
        """Iterate the supported evm chain managers"""
        for chain_id in get_args(SUPPORTED_CHAIN_IDS):
            yield self.get_evm_manager(chain_id)

    def flush_eth2_cache(self) -> None:
        """Flush cache for logic related to validators. We do this after modifying the list of
        validators since it affects the balances and stats"""
        self.flush_cache('get_eth2_staking_details')
        self.flush_cache('refresh_eth2_get_daily_stats')
        self.flush_cache('get_eth2_daily_stats')
        self.flush_cache('query_eth2_balances')
        self.flush_cache('query_balances')
        self.flush_cache('query_balances', blockchain=None, ignore_cache=False)
        self.flush_cache('query_balances', blockchain=None, ignore_cache=True)
        self.flush_cache('query_balances', blockchain=SupportedBlockchain.ETHEREUM_BEACONCHAIN, ignore_cache=False)  # noqa: E501
        self.flush_cache('query_balances', blockchain=SupportedBlockchain.ETHEREUM_BEACONCHAIN, ignore_cache=True)  # noqa: E501

    def get_all_counterparties(self) -> set['CounterpartyDetails']:
        """
        obtain the set of unique counterparties from the decoders across
        all the chains that have them.
        """
        return reduce(
            operator.or_,
            [
                self.get_evm_manager(chain_id).transactions_decoder.rules.all_counterparties
                for chain_id in EVM_CHAIN_IDS_WITH_TRANSACTIONS
            ],
        )
