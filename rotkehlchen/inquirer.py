import logging
import operator
import time
import random
from collections.abc import Callable, Iterable, Sequence
from contextlib import suppress
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NamedTuple,
    Optional,
    TypeVar,
    Union,
    cast,
    overload,
)

from rotkehlchen.assets.asset import Asset, AssetWithOracles, EvmToken, FiatAsset, UnderlyingToken, CustomAsset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.arbitrum_one.modules.umami.constants import CPT_UMAMI
from rotkehlchen.chain.arbitrum_one.modules.umami.utils import get_umami_vault_token_price
from rotkehlchen.chain.ethereum.defi.price import handle_defi_price_query
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CPT_AURA_FINANCE
from rotkehlchen.chain.evm.decoding.aura_finance.utils import get_aura_pool_price
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V1, CPT_BALANCER_V2
from rotkehlchen.chain.evm.decoding.balancer.utils import get_balancer_pool_price
from rotkehlchen.chain.evm.decoding.curve.constants import CURVE_CHAIN_ID_TYPE, CURVE_CHAIN_IDS
from rotkehlchen.chain.evm.decoding.curve_lend.utils import get_curve_lending_vault_token_price
from rotkehlchen.chain.evm.decoding.gearbox.gearbox_cache import (
    ensure_gearbox_lp_underlying_tokens,
    read_gearbox_data_from_cache,
)
from rotkehlchen.chain.evm.decoding.morpho.utils import get_morpho_vault_token_price
from rotkehlchen.chain.evm.decoding.uniswap.v3.utils import get_uniswap_v3_position_price
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.evm.utils import lp_price_from_uniswaplike_pool_contract
from rotkehlchen.chain.polygon_pos.constants import POLYGON_POS_POL_HARDFORK
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import (
    A_3CRV,
    A_BSQ,
    A_BTC,
    A_CRV_3CRV,
    A_CRV_3CRVSUSD,
    A_CRV_GUSD,
    A_CRV_RENWBTC,
    A_CRV_YPAX,
    A_CRVP_DAIUSDCTBUSD,
    A_CRVP_DAIUSDCTTUSD,
    A_CRVP_RENWSBTC,
    A_DAI,
    A_ETH,
    A_ETH2,
    A_FARM_CRVRENWBTC,
    A_FARM_DAI,
    A_FARM_RENBTC,
    A_FARM_TUSD,
    A_FARM_USDC,
    A_FARM_USDT,
    A_FARM_WBTC,
    A_FARM_WETH,
    A_KFEE,
    A_TUSD,
    A_USD,
    A_USDC,
    A_USDT,
    A_WETH,
    A_YV1_3CRV,
    A_YV1_ALINK,
    A_YV1_DAI,
    A_YV1_DAIUSDCTBUSD,
    A_YV1_DAIUSDCTTUSD,
    A_YV1_GUSD,
    A_YV1_RENWSBTC,
    A_YV1_TUSD,
    A_YV1_USDC,
    A_YV1_USDT,
    A_YV1_WETH,
    A_YV1_YFI,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import ethaddress_to_identifier, evm_address_to_identifier
from rotkehlchen.constants.timing import DAY_IN_SECONDS, MONTH_IN_SECONDS
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.defi import DefiPoolError
from rotkehlchen.errors.misc import (
    BlockchainQueryError,
    InputError,
    NotERC20Conformant,
    RemoteError,
)
from rotkehlchen.errors.price import PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.xratescom import (
    get_current_xratescom_exchange_rates,
    get_historical_xratescom_exchange_rates,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_get_unique_cache_value, read_curve_pool_tokens
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.oracles.structures import CurrentPriceOracle
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    CURVE_LENDING_VAULTS_PROTOCOL,
    CURVE_POOL_PROTOCOL,
    GEARBOX_PROTOCOL,
    HOP_PROTOCOL_LP,
    LP_TOKEN_AS_POOL_PROTOCOLS,
    MORPHO_VAULT_PROTOCOL,
    UNISWAPV3_PROTOCOL,
    YEARN_STAKING_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    YEARN_VAULTS_V3_PROTOCOL,
    CacheType,
    ChainID,
    EvmTokenKind,
    Price,
    ProtocolsWithPriceLogic,
    Timestamp,
)
from rotkehlchen.utils.data_structures import LRUCacheWithRemove
from rotkehlchen.utils.misc import timestamp_to_daystart_timestamp, ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import PenalizablePriceOracleMixin

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.manager import ArbitrumOneManager
    from rotkehlchen.chain.base.manager import BaseManager
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
    from rotkehlchen.chain.evm.manager import EvmManager
    from rotkehlchen.chain.gnosis.manager import GnosisManager
    from rotkehlchen.chain.optimism.manager import OptimismManager
    from rotkehlchen.chain.polygon_pos.manager import PolygonPOSManager
    from rotkehlchen.externalapis.alchemy import Alchemy
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.externalapis.defillama import Defillama
    from rotkehlchen.externalapis.yahoofinance import YahooFinance
    from rotkehlchen.globaldb.manual_price_oracles import ManualCurrentOracle
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CURRENT_PRICE_CACHE_SECS = 300  # 5 mins
DEFAULT_RATE_LIMIT_WAITING_TIME = 60  # seconds
BTC_PER_BSQ = FVal('0.00000100')  # 1 BST == 100 satoshi https://docs.bisq.network/dao/specification#bsq-token

ASSETS_UNDERLYING_BTC = (
    A_YV1_RENWSBTC,
    A_FARM_CRVRENWBTC,
    A_FARM_RENBTC,
    A_FARM_WBTC,
    A_CRV_RENWBTC,
    A_CRVP_RENWSBTC,
)


CurrentPriceOracleInstance = Union[
    'Coingecko',
    'Cryptocompare',
    'Defillama',
    'UniswapV3Oracle',
    'UniswapV2Oracle',
    'ManualCurrentOracle',
    'YahooFinance',
]


def _check_curve_contract_call(decoded: tuple[Any, ...]) -> bool:
    """
    Checks the result of decoding curve contract methods to verify:
    - The result is a tuple
    - It should return only one value
    - The value should be an integer
    Returns true if the decode was correct
    """
    return (
        isinstance(decoded, tuple) and
        len(decoded) == 1 and
        isinstance(decoded[0], int)
    )


def get_underlying_asset_price(token: EvmToken) -> tuple[Price | None, CurrentPriceOracle]:
    """Gets the underlying asset price for the given evm token

    TODO: This should be eventually pulled from the assets DB. All of these
    need to be updated, to contain proper protocol, and underlying assets.
    """
    price, oracle = None, CurrentPriceOracle.BLOCKCHAIN
    if token.protocol in LP_TOKEN_AS_POOL_PROTOCOLS:
        price = Inquirer().find_lp_price_from_uniswaplike_pool(token)
    elif token.protocol == CURVE_POOL_PROTOCOL:
        price = Inquirer().find_curve_pool_price(token)
    elif token.protocol == YEARN_VAULTS_V2_PROTOCOL:
        price = Inquirer().find_yearn_price(token, 'YEARN_VAULT_V2')
    elif token.protocol == YEARN_VAULTS_V3_PROTOCOL:
        price = Inquirer().find_yearn_price(token, 'YEARN_VAULT_V3')
    elif token.protocol == GEARBOX_PROTOCOL:
        price = Inquirer().find_gearbox_price(token)
    elif token.protocol == HOP_PROTOCOL_LP:
        price = Inquirer().find_hop_lp_price(token)
    elif token.protocol == YEARN_STAKING_PROTOCOL:
        price = Inquirer().find_yearn_staking_price(token)
    elif token.protocol == CPT_UMAMI:
        price = get_umami_vault_token_price(
            vault_token=token,
            inquirer=Inquirer(),  # Initialize here to avoid a circular import
            evm_inquirer=Inquirer.get_evm_manager(chain_id=ChainID.ARBITRUM_ONE).node_inquirer,
        )
    elif token.protocol == MORPHO_VAULT_PROTOCOL:
        price = get_morpho_vault_token_price(
            vault_token=token,
            inquirer=Inquirer(),  # Initialize here to avoid a circular import
            evm_inquirer=Inquirer.get_evm_manager(chain_id=token.chain_id).node_inquirer,
        )
    elif token.protocol == CURVE_LENDING_VAULTS_PROTOCOL:
        price = get_curve_lending_vault_token_price(
            vault_token=token,
            inquirer=Inquirer(),  # Initialize here to avoid a circular import
            evm_inquirer=Inquirer.get_evm_manager(chain_id=token.chain_id).node_inquirer,
        )
    elif token.protocol in (CPT_BALANCER_V1, CPT_BALANCER_V2):
        price = get_balancer_pool_price(
            pool_token=token,
            evm_inquirer=Inquirer.get_evm_manager(chain_id=token.chain_id).node_inquirer,
        )
    elif token.protocol == CPT_AURA_FINANCE:
        price = get_aura_pool_price(
            inquirer=Inquirer(),
            token=token,
        )
    elif token.protocol == UNISWAPV3_PROTOCOL:
        price = get_uniswap_v3_position_price(
            token=token,
            inquirer=Inquirer(),
            evm_inquirer=Inquirer.get_evm_manager(chain_id=token.chain_id).node_inquirer,
        )

    if token == A_FARM_DAI:
        price, oracle = Inquirer.find_usd_price_and_oracle(A_DAI)
    elif token == A_FARM_WETH:
        price, oracle = Inquirer.find_usd_price_and_oracle(A_ETH)
    elif token == A_FARM_USDT:
        price, oracle = Inquirer.find_usd_price_and_oracle(A_USDT)
    elif token == A_FARM_USDC:
        price, oracle = Inquirer.find_usd_price_and_oracle(A_USDC)
    elif token == A_FARM_TUSD:
        price, oracle = Inquirer.find_usd_price_and_oracle(A_TUSD)
    elif token in ASSETS_UNDERLYING_BTC:
        price, oracle = Inquirer.find_usd_price_and_oracle(A_BTC)
    elif token == 'eip155:1/erc20:0x815C23eCA83261b6Ec689b60Cc4a58b54BC24D8D':  # vTHOR
        price, oracle = Inquirer.find_usd_price_and_oracle(Asset('eip155:1/erc20:0xa5f2211B9b8170F694421f2046281775E8468044'))  # THOR token  # noqa: E501

    # At this point we have to return the price if it's not None. If we don't do this and got
    # a price for a token that has underlying assets, the code will enter the if statement after
    # this block and the value for price will change becoming incorrect.
    if price is not None:
        return price, oracle

    if token.underlying_tokens is not None:
        usd_price = ZERO
        for underlying_token in token.underlying_tokens:
            token = EvmToken(underlying_token.get_identifier(parent_chain=token.chain_id))
            underlying_asset_price, oracle = Inquirer.find_usd_price_and_oracle(token)
            usd_price += underlying_asset_price * underlying_token.weight

        if usd_price != ZERO_PRICE:
            price = Price(usd_price)

    return price, oracle


T = TypeVar('T', bound=Callable[..., Any])


class CachedPriceEntry(NamedTuple):
    price: Price
    time: Timestamp
    oracle: CurrentPriceOracle


class Inquirer:
    __instance: Optional['Inquirer'] = None
    _cached_forex_data: dict
    _cached_current_price: LRUCacheWithRemove[tuple[Asset, Asset], CachedPriceEntry]
    _data_directory: Path
    _cryptocompare: 'Cryptocompare'
    _coingecko: 'Coingecko'
    _alchemy: 'Alchemy'
    _defillama: 'Defillama'
    _yahoofinance: 'YahooFinance'
    _manualcurrent: 'ManualCurrentOracle'
    _uniswapv2: Optional['UniswapV2Oracle'] = None
    _uniswapv3: Optional['UniswapV3Oracle'] = None
    _evm_managers: dict[ChainID, 'EvmManager']
    _oracles: Sequence[CurrentPriceOracle] | None = None
    _oracle_instances: list[CurrentPriceOracleInstance] | None = None
    _oracles_not_onchain: Sequence[CurrentPriceOracle] | None = None
    _oracle_instances_not_onchain: list[CurrentPriceOracleInstance] | None = None
    _msg_aggregator: 'MessagesAggregator'
    # save only the identifier of the special tokens since we only check if assets are in this set
    special_tokens: set[str]
    weth: EvmToken
    usd: FiatAsset
    
    # Persistent storage for custom asset prices to avoid them being wiped out
    _custom_asset_prices: dict[str, Price] = {}
    # Add new structure to track stock/ETF prices with timestamps
    _stock_etf_prices: dict[str, tuple[Price, int]] = {}  # Maps identifier to (price, timestamp)

    def __new__(
            cls,
            data_dir: Path | None = None,
            cryptocompare: Optional['Cryptocompare'] = None,
            coingecko: Optional['Coingecko'] = None,
            defillama: Optional['Defillama'] = None,
            alchemy: Optional['Alchemy'] = None,
            yahoofinance: Optional['YahooFinance'] = None,
            manualcurrent: Optional['ManualCurrentOracle'] = None,
            msg_aggregator: Optional['MessagesAggregator'] = None,
    ) -> 'Inquirer':
        """Create or get the already existing singleton.

        In case of multi processing initialization avoid using `clear`
        when you just want to setup the state (e.g. in tests).
        """
        if Inquirer.__instance is not None:
            return Inquirer.__instance

        error_msg = 'arguments should be given at the first instantiation'
        assert data_dir, error_msg
        assert cryptocompare, error_msg
        assert coingecko, error_msg
        assert defillama, error_msg
        assert alchemy, error_msg
        assert yahoofinance, error_msg
        assert manualcurrent, error_msg
        assert msg_aggregator, error_msg

        Inquirer.__instance = object.__new__(cls)
        # Initialize both instance and class attributes for backward compatibility
        Inquirer.__instance._cached_forex_data = {}
        Inquirer.__instance._cached_current_price = LRUCacheWithRemove(2048)
        Inquirer._cached_current_price = Inquirer.__instance._cached_current_price  # Make it accessible as class attr too
        Inquirer._data_directory = data_dir
        Inquirer._cryptocompare = cryptocompare
        Inquirer._coingecko = coingecko
        Inquirer._defillama = defillama
        Inquirer._alchemy = alchemy
        Inquirer._yahoofinance = yahoofinance
        Inquirer._manualcurrent = manualcurrent
        Inquirer._evm_managers = {}
        Inquirer._oracles = None
        Inquirer._oracle_instances = None
        Inquirer._oracles_not_onchain = None
        Inquirer._oracle_instances_not_onchain = None
        Inquirer._msg_aggregator = msg_aggregator
        Inquirer.special_tokens = {
            A_YV1_DAIUSDCTBUSD.identifier,
            A_CRVP_DAIUSDCTBUSD.identifier,
            A_CRVP_DAIUSDCTTUSD.identifier,
            A_YV1_DAIUSDCTTUSD.identifier,
            A_YV1_DAIUSDCTTUSD.identifier,
            A_CRVP_RENWSBTC.identifier,
            A_YV1_RENWSBTC.identifier,
            A_CRV_RENWBTC.identifier,
            A_CRV_YPAX.identifier,
            A_CRV_GUSD.identifier,
            A_CRV_3CRV.identifier,
            A_YV1_3CRV.identifier,
            A_CRV_3CRVSUSD.identifier,
            A_YV1_ALINK.identifier,
            A_YV1_DAI.identifier,
            A_YV1_WETH.identifier,
            A_YV1_YFI.identifier,
            A_YV1_USDT.identifier,
            A_YV1_USDC.identifier,
            A_YV1_TUSD.identifier,
            A_YV1_GUSD.identifier,
            A_FARM_USDC.identifier,
            A_FARM_USDT.identifier,
            A_FARM_DAI.identifier,
            A_FARM_TUSD.identifier,
            A_FARM_WETH.identifier,
            A_FARM_WBTC.identifier,
            A_FARM_RENBTC.identifier,
            A_FARM_CRVRENWBTC.identifier,
            A_3CRV.identifier,
            'eip155:1/erc20:0x815C23eCA83261b6Ec689b60Cc4a58b54BC24D8D',  # vTHOR
        }
        
        # Initialize persistent price cache
        Inquirer.initialize_price_cache()
        
        try:
            Inquirer.usd = A_USD.resolve_to_fiat_asset()
            Inquirer.weth = A_WETH.resolve_to_evm_token()
        except (UnknownAsset, WrongAssetType) as e:
            message = f'One of the base assets was deleted/modified from the DB: {e!s}'
            log.critical(message)
            raise RuntimeError(message + '. Add it back manually or contact support') from e

        return Inquirer.__instance

    @staticmethod
    def inject_evm_managers(evm_managers: Sequence[tuple[ChainID, 'EvmManager']]) -> None:
        instance = Inquirer()
        for chain_id, evm_manager in evm_managers:
            instance._evm_managers[chain_id] = evm_manager

    @overload
    @staticmethod
    def get_evm_manager(chain_id: CURVE_CHAIN_ID_TYPE) -> 'ArbitrumOneManager | BaseManager | EthereumManager | GnosisManager | OptimismManager | PolygonPOSManager':  # noqa: E501
        ...

    @overload
    @staticmethod
    def get_evm_manager(chain_id: ChainID) -> 'EvmManager':
        ...

    @staticmethod
    def get_evm_manager(chain_id: ChainID | CURVE_CHAIN_ID_TYPE) -> 'EvmManager':
        evm_manager = Inquirer._evm_managers.get(chain_id)
        assert evm_manager is not None, f'evm manager for chain id {chain_id} should have been injected'  # noqa: E501
        return evm_manager

    @staticmethod
    def add_defi_oracles(
            uniswap_v2: Optional['UniswapV2Oracle'],
            uniswap_v3: Optional['UniswapV3Oracle'],
    ) -> None:
        Inquirer()._uniswapv2 = uniswap_v2
        Inquirer()._uniswapv3 = uniswap_v3

    @staticmethod
    def _get_cache() -> LRUCacheWithRemove:
        """Safely get the current price cache, handling either instance or class attribute."""
        if Inquirer.__instance is not None and hasattr(Inquirer.__instance, '_cached_current_price'):
            return Inquirer.__instance._cached_current_price
        if hasattr(Inquirer, '_cached_current_price'):
            return Inquirer._cached_current_price
        # If neither is available, create a new one as a fallback
        return LRUCacheWithRemove(2048)

    @staticmethod
    def get_cached_current_price_entry(
            cache_key: tuple[Asset, Asset],
    ) -> CachedPriceEntry | None:
        """Get a price entry from the cache if it's recent enough.

        Return None if it's not in the cache or if it's too old.
        """
        cache = Inquirer._get_cache().get(cache_key)
        if cache is None or ts_now() - cache.time > CURRENT_PRICE_CACHE_SECS:
            return None

        return cache

    @staticmethod
    def remove_cache_prices_for_asset(assets_to_invalidate: set[Asset]) -> None:
        """Deletes all prices cache that contains any asset in the possible pairs."""
        for asset_pair in list(Inquirer._get_cache().cache):  # create a list to avoid mutating the map while iterating it  # noqa: E501
            if asset_pair[0] in assets_to_invalidate or asset_pair[1] in assets_to_invalidate:
                Inquirer._get_cache().remove(asset_pair)

    @staticmethod
    def set_oracles_order(oracles: Sequence[CurrentPriceOracle]) -> None:
        assert len(oracles) != 0 and len(oracles) == len(set(oracles)), (
            "Oracles can't be empty or have repeated items"
        )
        instance = Inquirer()
        instance._oracles = oracles
        instance._oracle_instances = [getattr(instance, f'_{oracle!s}') for oracle in instance._oracles]  # noqa: E501
        instance._oracles_not_onchain = []
        instance._oracle_instances_not_onchain = []
        for oracle, oracle_instance in zip(instance._oracles, instance._oracle_instances, strict=True):  # noqa: E501
            if oracle not in (CurrentPriceOracle.UNISWAPV2, CurrentPriceOracle.UNISWAPV3):
                instance._oracles_not_onchain.append(oracle)
                instance._oracle_instances_not_onchain.append(oracle_instance)

    @staticmethod
    def set_cached_price(cache_key: tuple[Asset, Asset], cached_price: CachedPriceEntry) -> None:
        """Set a price entry in the cache and for all assets with the same collection in
        rotki_glob.db
        """
        Inquirer._get_cache().add(cache_key, cached_price)

        # Also add it for all assets with the same collection main_asset_identifier
        # We assume that the price of all the assets in a collection is the same
        related_assets = GlobalDBHandler.get_assets_in_same_collection(cache_key[0].identifier)
        for related_asset in related_assets:
            Inquirer._get_cache().add((related_asset, cache_key[1]), cached_price)

    @staticmethod
    def _try_oracle_price_query(
            oracle: CurrentPriceOracle,
            oracle_instance: CurrentPriceOracleInstance,
            from_assets: list[AssetWithOracles],
            to_asset: AssetWithOracles,
    ) -> tuple[dict[AssetWithOracles, Price], list[AssetWithOracles]]:
        """Tries to query the current prices of the from_assets
        in to_asset valuation, using the provided oracle instance.
        Returns a tuple containing a dict mapping assets to prices
        and a list of assets for which no price was found.
        """
        try:
            prices = oracle_instance.query_multiple_current_prices(
                from_assets=from_assets,
                to_asset=to_asset,
            )
        except (DefiPoolError, PriceQueryUnsupportedAsset, RemoteError) as e:
            log.warning(
                f'Current price oracle {oracle_instance} failed to request {to_asset!s} '
                f'price for {from_assets!s} due to: {e!s}.',
            )
            return {}, from_assets

        failed_assets, now = [], ts_now()
        for from_asset in from_assets:
            if (price := prices.get(from_asset, ZERO_PRICE)) != ZERO_PRICE:
                Inquirer.set_cached_price(
                    cache_key=(from_asset, to_asset),
                    cached_price=CachedPriceEntry(
                        price=price,
                        time=now,
                        oracle=oracle,
                    ),
                )
            else:  # Either from_asset was recorded with ZERO_PRICE or it is not present in prices
                prices.pop(from_asset, None)
                failed_assets.append(from_asset)

        return prices, failed_assets

    @staticmethod
    def _query_oracle_instances(
            from_assets: list[Asset],
            to_asset: Asset,
            skip_onchain: bool = False,
    ) -> dict[Asset, tuple[Price, CurrentPriceOracle]]:
        """Query oracle instances.
        Returns a dict mapping assets to a tuple of the price found and the oracle used.
        If no oracles are able to find an asset's price it will be set to ZERO_PRICE.
        """
        instance = Inquirer()
        assert (
            instance._oracles is not None and
            instance._oracle_instances is not None and
            instance._oracles_not_onchain is not None and
            instance._oracle_instances_not_onchain is not None
        ), 'Inquirer should never be called before setting the oracles'

        # Resolve assets to AssetWithOracles and set
        # the price of any assets without oracles to ZERO_PRICE
        found_prices, unpriced_assets = {}, []
        to_asset = to_asset.resolve_to_asset_with_oracles()
        
        # First, check for any custom assets that might need special handling
        # This is a non-intrusive addition that doesn't alter the existing flow
        yahoo_finance_instance = instance._yahoofinance
        for from_asset in from_assets:
            # Special handling for custom assets (stock/ETF)
            try:
                if hasattr(from_asset, 'get_asset_type') and from_asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                    # Try to get the actual CustomAsset instance
                    try:
                        from rotkehlchen.assets.asset import CustomAsset
                        from rotkehlchen.assets.types import AssetType
                        
                        custom_asset = from_asset.resolve()
                        if isinstance(custom_asset, CustomAsset) and hasattr(custom_asset, 'custom_asset_type'):
                            if custom_asset.custom_asset_type.lower() in ('stock', 'etf'):
                                # Direct query to Yahoo Finance for this stock/ETF
                                price = yahoo_finance_instance.query_custom_asset_price(
                                    custom_asset=custom_asset,
                                    to_currency=to_asset.symbol
                                )
                                if price != ZERO_PRICE:
                                    log.debug(
                                        f'Got price for custom asset via special handler',
                                        asset=from_asset.identifier,
                                        price=price,
                                    )
                                    found_prices[from_asset] = price, CurrentPriceOracle.YAHOOFINANCE
                                    # Skip this asset in the normal flow
                                    continue
                    except Exception as e:
                        log.warning(
                            f'Failed to get price for custom asset',
                            asset=from_asset.identifier,
                            error=str(e),
                        )
            except Exception:
                # If any error occurs in our custom handling, just continue with normal flow
                pass
            
            # Normal asset handling flow (unmodified)
            if from_asset.is_asset_with_oracles():
                unpriced_assets.append(from_asset.resolve_to_asset_with_oracles())
            else:
                found_prices[from_asset] = ZERO_PRICE, CurrentPriceOracle.BLOCKCHAIN

        if len(unpriced_assets) == 0:
            return found_prices  # no assets with oracles found. Skip querying oracles.

        if skip_onchain:
            oracles = instance._oracles_not_onchain
            oracle_instances = instance._oracle_instances_not_onchain
        else:
            oracles = instance._oracles
            oracle_instances = instance._oracle_instances

        for oracle, oracle_instance in zip(oracles, oracle_instances, strict=True):
            if (
                isinstance(oracle_instance, CurrentPriceOracleInterface) and
                (
                    oracle_instance.rate_limited_in_last(DEFAULT_RATE_LIMIT_WAITING_TIME) is True or  # noqa: E501
                    (isinstance(oracle_instance, PenalizablePriceOracleMixin) and oracle_instance.is_penalized() is True)  # noqa: E501
                )
            ):
                continue

            prices, unpriced_assets = Inquirer._try_oracle_price_query(
                oracle=oracle,
                oracle_instance=oracle_instance,
                from_assets=unpriced_assets,
                to_asset=to_asset,
            )
            for from_asset, price in prices.items():
                log.debug(
                    f'Current price oracle {oracle} got price',
                    from_asset=from_asset,
                    to_asset=to_asset,
                    price=price,
                )
                found_prices[from_asset] = price, oracle

            if len(unpriced_assets) == 0:
                break

        # Set any assets that are still unknown to zero price
        found_prices.update(dict.fromkeys(unpriced_assets, (ZERO_PRICE, CurrentPriceOracle.BLOCKCHAIN)))  # noqa: E501
        return found_prices

    @staticmethod
    def _get_manual_prices(
            from_assets: list[Asset],
            to_asset: Asset,
    ) -> tuple[list[Asset], dict[Asset, tuple[Price, CurrentPriceOracle]]]:
        """Get manual prices. The type ignores are due to _try_oracle_price_query expecting
        AssetWithOracles, but we only use Asset here since the manual oracle can handle that.
        """
        found_prices = {}
        prices: dict[Asset, Price]
        unpriced_assets: list[Asset]
        prices, unpriced_assets = Inquirer._try_oracle_price_query(  # type: ignore[assignment]
            oracle=CurrentPriceOracle.MANUALCURRENT,
            oracle_instance=Inquirer._manualcurrent,
            from_assets=from_assets,  # type: ignore[arg-type]
            to_asset=to_asset,  # type: ignore[arg-type]
        )
        for from_asset, price in prices.items():
            found_prices[from_asset] = price, CurrentPriceOracle.MANUALCURRENT

        return unpriced_assets, found_prices

    @staticmethod
    def _get_special_usd_prices(
            from_assets: list[Asset],
            to_asset: Asset,
    ) -> tuple[list[Asset], dict[Asset, tuple[Price, CurrentPriceOracle]]]:
        """Handle some special cases when finding usd prices.
        Returns a tuple containing a list of assets without prices and a dict of found prices.
        If to_asset is not USD, it will simply return from_assets and an empty dict.
        """
        if to_asset != A_USD:
            return from_assets, {}

        found_prices, assets_without_special_price = {}, []
        for from_asset in from_assets:
            if from_asset == A_BSQ:
                # BSQ is defined as 100 satohis but can be traded. Before we were using an api
                # to query the BSQ market but it isn't available anymore so we assume BTC_PER_BSQ
                # to obtain a price based on BTC price.
                btc_price = Inquirer.find_usd_price(A_BTC)
                found_prices[from_asset] = Price(BTC_PER_BSQ * btc_price), CurrentPriceOracle.BLOCKCHAIN  # noqa: E501
            elif from_asset == A_KFEE:  # KFEE is a kraken special asset where 1000 KFEE = 10 USD
                found_prices[from_asset] = Price(FVal(0.01)), CurrentPriceOracle.FIAT
            elif (price_and_oracle := Inquirer._maybe_get_evm_token_usd_price(asset=from_asset)) is not None:  # noqa: E501
                found_prices[from_asset] = price_and_oracle
            else:
                assets_without_special_price.append(from_asset)

        return assets_without_special_price, found_prices

    @staticmethod
    def _maybe_get_evm_token_usd_price(asset: Asset) -> tuple[Price, CurrentPriceOracle] | None:
        """Maybe get an evm token's usd price via its underlying tokens or protocol logic.
        Returns a tuple containing the usd price and the oracle used or None if the specified
        asset is not an evm token, if it has itself as an underlying token or if no price is found.
        """
        try:
            asset = asset.resolve_to_evm_token()
        except (UnknownAsset, WrongAssetType):
            return None

        if (  # Prevent recursion if this asset has itself as an underlying token
            (underlying_tokens := asset.underlying_tokens) is not None and
            asset.evm_address in (x.address for x in underlying_tokens)
        ):
            Inquirer._msg_aggregator.add_error(
                f'Token {asset} has itself as underlying token. Please edit the '
                'asset to fix it. Price queries will not work until this is done.',
            )
            return None

        price_result, oracle = None, CurrentPriceOracle.BLOCKCHAIN
        if asset.identifier in Inquirer.special_tokens:
            ethereum = Inquirer.get_evm_manager(chain_id=ChainID.ETHEREUM)
            underlying_asset_price, oracle = get_underlying_asset_price(asset)
            price_result = handle_defi_price_query(
                ethereum=ethereum.node_inquirer,  # type:ignore  # ethereum is an EthereumManager so the inquirer is of the expected type
                token=asset,
                underlying_asset_price=underlying_asset_price,
            )
        elif (
            asset.protocol in ProtocolsWithPriceLogic or
            underlying_tokens is not None
        ):
            price_result, oracle = get_underlying_asset_price(asset)

        if price_result is None or price_result == ZERO_PRICE:
            return None

        Inquirer.set_cached_price(
            cache_key=(asset, A_USD),
            cached_price=CachedPriceEntry(
                price=(price := Price(price_result)),
                time=ts_now(),
                oracle=oracle,
            ),
        )
        return price, oracle

    @staticmethod
    def _maybe_replace_asset(asset: Asset) -> Asset:
        """Get the asset to actually use when finding the price of the specified asset.
        Uses the main asset for collection assets and also handles special cases like ETH2 and POL.
        Returns either a replacement asset, or the original asset.
        """
        if asset == A_ETH2:
            return A_ETH
        elif (
            (collection_main_asset_id := GlobalDBHandler.get_collection_main_asset(asset.identifier)) is not None and  # noqa: E501
            (collection_main_asset_id != 'eip155:1/erc20:0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6' or ts_now() > POLYGON_POS_POL_HARDFORK)  # only use the pol token after the hardfork.  # noqa: E501
        ):
            return Asset(collection_main_asset_id)

        return asset

    @staticmethod
    def _preprocess_assets_to_query(
            from_assets: list[Asset],
            to_asset: Asset,
            ignore_cache: bool = False,
    ) -> tuple[dict[Asset, tuple[Price, CurrentPriceOracle]], dict[Asset, Asset], list[Asset]]:
        """Preprocess assets before querying prices, handling replacements, cached prices, etc.
        Returns a tuple containing a dict of found asset prices, a dict of replaced assets,
        and a list of assets that still need their prices queried.
        """
        found_prices, replaced_assets, unpriced_assets = {}, {}, []
        
        # Special handling for custom assets to ensure we use cached prices
        # This needs to be done separately at the start to prevent any bypassing
        if ignore_cache:
            log.debug(f"Running _preprocess_assets_to_query with ignore_cache=True for {len(from_assets)} assets")
            
            # Check for any custom assets (both stock/ETF and other types like cars)
            custom_assets = []
            for asset in from_assets:
                try:
                    if hasattr(asset, 'get_asset_type') and asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                        # Add to custom assets list
                        custom_assets.append(asset)
                except Exception:
                    continue
                    
            if custom_assets:
                log.info(f"Found {len(custom_assets)} custom assets in price query - ensuring cached values are used")
                
                # For each custom asset, check if we have a cached price
                for asset in custom_assets:
                    # First check our persistent storage
                    stored_price = Inquirer._get_custom_asset_price(asset)
                    if stored_price is not None and stored_price != ZERO_PRICE:
                        # Add to found prices with manual oracle to ensure it's used
                        found_prices[asset] = stored_price, CurrentPriceOracle.MANUALCURRENT
                        log.debug(
                            f"Using stored custom asset price during refresh",
                            asset=asset.identifier,
                            price=stored_price
                        )
                    # Also check directly in the _custom_asset_prices dictionary
                    elif hasattr(asset, 'identifier') and asset.identifier in Inquirer._custom_asset_prices:
                        stored_price = Inquirer._custom_asset_prices[asset.identifier]
                        found_prices[asset] = stored_price, CurrentPriceOracle.MANUALCURRENT
                        log.debug(
                            f"Using price from _custom_asset_prices dictionary during refresh",
                            asset=asset.identifier,
                            price=stored_price
                        )
                    # Also check the normal price cache with high priority
                    elif (cache_key := (asset, to_asset)) and (cache := Inquirer.get_cached_current_price_entry(cache_key=cache_key)) is not None:
                        found_prices[asset] = cache.price, cache.oracle
                        log.debug(
                            f"Using price from cache during refresh",
                            asset=asset.identifier,
                            price=cache.price
                        )
        
        for from_asset in from_assets:
            # Skip if we already handled this asset above
            if from_asset in found_prices:
                continue
                
            if from_asset == to_asset:
                found_prices[from_asset] = Price(ONE), CurrentPriceOracle.MANUALCURRENT
                continue

            if (asset_to_price := Inquirer._maybe_replace_asset(asset=from_asset)) != from_asset:
                replaced_assets[from_asset] = asset_to_price
                if asset_to_price in found_prices or asset_to_price in unpriced_assets:
                    continue

            # Special protection for ALL custom assets
            # Make sure we don't ignore cache for these since we want to preserve any prices we got
            use_cache_for_this_asset = not ignore_cache
            if hasattr(from_asset, 'get_asset_type') and from_asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                # Force using cache for all custom assets
                log.debug(
                    f"Using cache for custom asset regardless of ignore_cache setting",
                    asset=from_asset.identifier,
                    original_ignore_cache=ignore_cache
                )
                use_cache_for_this_asset = True
                
                # Also check if we have a manually set price in our custom asset prices dictionary
                if hasattr(from_asset, 'identifier') and from_asset.identifier in Inquirer._custom_asset_prices:
                    stored_price = Inquirer._custom_asset_prices[from_asset.identifier]
                    found_prices[from_asset] = stored_price, CurrentPriceOracle.MANUALCURRENT
                    log.debug(
                        f"Using stored custom asset price from dictionary",
                        asset=from_asset.identifier,
                        price=stored_price
                    )
                    continue

            if (
                use_cache_for_this_asset and
                (cache := Inquirer.get_cached_current_price_entry(cache_key=(asset_to_price, to_asset))) is not None  # noqa: E501
            ):
                found_prices[asset_to_price] = cache.price, cache.oracle
                continue

            try:  # Ensure the asset exists
                unpriced_assets.append(asset_to_price.check_existence())
            except UnknownAsset:
                log.warning(
                    f'Tried to query price for an unknown/unsupported asset: {asset_to_price}',
                )
                # Return ZERO_PRICE for non-existing assets
                found_prices[asset_to_price] = ZERO_PRICE, CurrentPriceOracle.BLOCKCHAIN

        return found_prices, replaced_assets, unpriced_assets

    @staticmethod
    def _find_prices(
            from_assets: list[Asset],
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, tuple[Price, CurrentPriceOracle]]:
        """Returns a dict mapping from_assets to tuples containing the current price of the
        from_asset in to_asset valuation and the oracle that was used to get that price.

        Note: For special assets, only USD prices are supported in _get_special_usd_prices.

        If all options for finding a price are unsuccessful the price will be set to ZERO_PRICE,
        and any errors will be logged in the logs.
        """
        found_prices, replaced_assets, unpriced_assets = Inquirer._preprocess_assets_to_query(
            from_assets=from_assets,
            to_asset=to_asset,
            ignore_cache=ignore_cache,
        )
        if len(unpriced_assets) != 0:
            for func in (
                Inquirer._get_manual_prices,
                Inquirer._query_fiat_pairs,
                Inquirer._get_special_usd_prices,
            ):
                unpriced_assets, new_found_prices = func(
                    from_assets=unpriced_assets,
                    to_asset=to_asset,
                )
                found_prices.update(new_found_prices)
                if len(unpriced_assets) == 0:
                    break
            else:
                found_prices.update(Inquirer._query_oracle_instances(
                    from_assets=unpriced_assets,
                    to_asset=to_asset,
                    skip_onchain=skip_onchain,
                ))

        # Only include the assets that were originally requested.
        for original_asset, replacement_asset in replaced_assets.items():
            found_prices[original_asset] = found_prices[replacement_asset]
            if replacement_asset not in from_assets:
                del found_prices[replacement_asset]

        return found_prices

    @staticmethod
    def find_price(
            from_asset: Asset,
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> Price:
        """Wrapper for find_prices to get the price of a single asset."""
        return Inquirer.find_prices(
            from_assets=[from_asset],
            to_asset=to_asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        ).get(from_asset, ZERO_PRICE)

    @staticmethod
    def find_price_and_oracle(
            from_asset: Asset,
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> tuple[Price, CurrentPriceOracle]:
        """Wrapper for find_prices_and_oracles to get the price and oracle for a single asset."""
        return Inquirer.find_prices_and_oracles(
            from_assets=[from_asset],
            to_asset=to_asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        ).get(from_asset, (ZERO_PRICE, CurrentPriceOracle.BLOCKCHAIN))

    @staticmethod
    def find_prices(
            from_assets: list[Asset],
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, Price]:
        """Wrapper for _find_prices to ignore the oracle queried when getting prices."""
        # SPECIAL PROTECTION: First, identify and preserve stock/ETF asset prices
        # This serves as a key intercept point for price refreshes
        result_prices = {}
        remaining_assets = []
        
        # Look for stock/ETF custom assets in our from_assets
        for asset in from_assets:
            # Special case for USD -> USD conversion
            if asset == to_asset:
                result_prices[asset] = Price(ONE)
                continue
            
            # Protection for stock/ETF custom assets against refresh
            if to_asset == A_USD and hasattr(asset, 'get_asset_type') and asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                try:
                    # Check if this is a stock/ETF type - these get special protection
                    custom_asset = asset.resolve()
                    if (isinstance(custom_asset, CustomAsset) and 
                        hasattr(custom_asset, 'custom_asset_type') and 
                        custom_asset.custom_asset_type.lower() in ('stock', 'etf')):
                        
                        # First check our persistent storage
                        stored_price = Inquirer._get_custom_asset_price(asset)
                        if stored_price is not None:
                            log.info(
                                f"Using persisted price for stock/ETF during refresh",
                                asset=custom_asset.identifier,
                                name=custom_asset.name,
                                price=stored_price
                            )
                            result_prices[asset] = stored_price
                            continue
                            
                        # If we don't have a stored price, try Yahoo Finance
                        yahoo = Inquirer()._yahoofinance
                        if yahoo:
                            price = yahoo.query_custom_asset_price(
                                custom_asset=custom_asset,
                                to_currency='USD'
                            )
                            if price != ZERO_PRICE:
                                log.info(
                                    f"Protected price lookup for stock/ETF during refresh",
                                    asset=custom_asset.identifier,
                                    name=custom_asset.name,
                                    price=price
                                )
                                result_prices[asset] = price
                                # Store for future reference
                                Inquirer._store_custom_asset_price(asset, price)
                                continue
                except Exception as e:
                    log.error(
                        f"Error in stock/ETF protection during refresh: {str(e)}",
                        asset=getattr(asset, 'identifier', 'unknown')
                    )
            
            # All other assets go through normal processing
            remaining_assets.append(asset)
                    
        # Process remaining assets with normal flow
        if remaining_assets:
            normal_prices = {
                asset: price_and_oracle[0]
                for asset, price_and_oracle in Inquirer._find_prices(
                    from_assets=remaining_assets,
                    to_asset=to_asset,
                    ignore_cache=ignore_cache,
                    skip_onchain=skip_onchain,
                ).items()
            }
            # Merge the results
            result_prices.update(normal_prices)
            
        # FINAL PROTECTION: Ensure stock/ETF assets still have their prices
        # This catches any that might have been added to result_prices with zero value
        for asset in from_assets:
            if (to_asset == A_USD and 
                asset in result_prices and 
                result_prices[asset] == ZERO_PRICE and 
                hasattr(asset, 'get_asset_type') and 
                asset.get_asset_type() == AssetType.CUSTOM_ASSET):
                try:
                    custom_asset = asset.resolve()
                    if (isinstance(custom_asset, CustomAsset) and 
                        hasattr(custom_asset, 'custom_asset_type') and 
                        custom_asset.custom_asset_type.lower() in ('stock', 'etf')):
                        
                        # Check persistent storage one more time
                        stored_price = Inquirer._get_custom_asset_price(asset)
                        if stored_price is not None and stored_price != ZERO_PRICE:
                            log.warning(
                                f"Recovering zeroed-out stock/ETF price from persistent storage",
                                asset=custom_asset.identifier,
                                name=custom_asset.name,
                                price=stored_price
                            )
                            result_prices[asset] = stored_price
                except Exception:
                    pass
            
        return result_prices

    @staticmethod
    def find_prices_and_oracles(
            from_assets: list[Asset],
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, tuple[Price, CurrentPriceOracle]]:
        """Wrapper for _find_prices to include the oracle queried when getting prices."""
        return Inquirer._find_prices(
            from_assets=from_assets,
            to_asset=to_asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        )

    @staticmethod
    def _store_custom_asset_price(asset: Asset, price: Price) -> None:
        """Store a custom asset price in our persistent storage to prevent it being reset.
        
        Args:
            asset: The asset to store the price for
            price: The price to store
        """
        if hasattr(asset, 'identifier'):
            log.info(
                f"Storing persistent price for custom asset",
                asset=asset.identifier,
                price=price
            )
            # Store in memory
            Inquirer._custom_asset_prices[asset.identifier] = price
            
            # Determine if this is a stock/ETF
            is_stock_etf = False
            asset_type = "unknown"
            try:
                if hasattr(asset, 'get_asset_type') and asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                    custom_asset = asset.resolve()
                    if isinstance(custom_asset, CustomAsset) and hasattr(custom_asset, 'custom_asset_type'):
                        asset_type = custom_asset.custom_asset_type.lower()
                        is_stock_etf = asset_type in ('stock', 'etf')
            except Exception as e:
                log.debug(f"Error determining asset type: {e}")
            
            # Store in the stock/ETF specific cache if this is a stock/ETF
            if is_stock_etf:
                # Also store with timestamp in the stock/ETF specific cache
                Inquirer._stock_etf_prices[asset.identifier] = (price, int(ts_now()))
                log.debug(
                    f"Stored stock/ETF price with timestamp",
                    asset=asset.identifier,
                    price=price,
                    asset_type=asset_type
                )
            else:
                log.debug(
                    f"Stored custom asset price (non-stock/ETF)",
                    asset=asset.identifier,
                    price=price,
                    asset_type=asset_type
                )
            
            # Try to store to disk as well for persistence across restarts
            # This is a best-effort attempt
            try:
                instance = Inquirer()
                if hasattr(instance, '_data_directory'):
                    import json
                    import os
                    
                    # Ensure the directory exists
                    cache_dir = os.path.join(instance._data_directory, 'cache')
                    os.makedirs(cache_dir, exist_ok=True)
                    
                    # Get existing data
                    cache_file = os.path.join(cache_dir, 'custom_asset_prices.json')
                    data = {}
                    if os.path.exists(cache_file):
                        try:
                            with open(cache_file, 'r') as f:
                                data = json.load(f)
                        except Exception as e:
                            # Start fresh if file is corrupt
                            log.warning(f"Custom asset price cache file corrupt, starting fresh: {e}")
                            data = {}
                    
                    # Add/update the price
                    data[asset.identifier] = float(price)
                    
                    # Write back to disk
                    with open(cache_file, 'w') as f:
                        json.dump(data, f)
                    
                    log.debug(f"Saved custom asset price to disk cache", asset=asset.identifier)
                    
                    # Also save special stock/ETF prices with timestamps if this is a stock/ETF
                    if is_stock_etf:
                        stock_etf_file = os.path.join(cache_dir, 'stock_etf_prices.json')
                        stock_data = {}
                        if os.path.exists(stock_etf_file):
                            try:
                                with open(stock_etf_file, 'r') as f:
                                    stock_data = json.load(f)
                            except Exception as e:
                                # Start fresh if file is corrupt
                                log.warning(f"Stock/ETF price cache file corrupt, starting fresh: {e}")
                                stock_data = {}
                        
                        # Store with timestamp
                        stock_data[asset.identifier] = {
                            "price": float(price),
                            "timestamp": int(ts_now())
                        }
                        
                        # Write stock/ETF data to disk
                        with open(stock_etf_file, 'w') as f:
                            json.dump(stock_data, f)
                            
                        log.debug(f"Saved stock/ETF price to special disk cache", asset=asset.identifier)
            except Exception as e:
                # Non-fatal if we can't save to disk
                log.error(f"Could not save custom asset price to disk: {e}")
                log.debug(f"Error details: {str(e)}")

    @staticmethod
    def _initialize_custom_asset_prices() -> None:
        """Load custom asset prices from disk cache.
        
        This should be called during application startup to restore persisted prices.
        """
        try:
            instance = Inquirer()
            if hasattr(instance, '_data_directory'):
                import json
                import os
                
                # Load general custom asset prices
                cache_file = os.path.join(instance._data_directory, 'cache', 'custom_asset_prices.json')
                if os.path.exists(cache_file):
                    try:
                        with open(cache_file, 'r') as f:
                            data = json.load(f)
                        
                        # Restore prices to memory
                        for asset_id, price_float in data.items():
                            Inquirer._custom_asset_prices[asset_id] = Price(FVal(price_float))
                            
                        log.info(f"Loaded {len(data)} custom asset prices from disk cache")
                    except Exception as e:
                        log.error(f"Failed to load custom asset prices from {cache_file}: {e}")
                else:
                    log.debug(f"No custom asset price cache file found at {cache_file}")
                
                # Also load stock/ETF specific prices with timestamps
                stock_etf_file = os.path.join(instance._data_directory, 'cache', 'stock_etf_prices.json')
                if os.path.exists(stock_etf_file):
                    try:
                        with open(stock_etf_file, 'r') as f:
                            stock_data = json.load(f)
                        
                        # Restore stock/ETF prices to memory
                        for asset_id, price_info in stock_data.items():
                            if isinstance(price_info, dict) and 'price' in price_info and 'timestamp' in price_info:
                                Inquirer._stock_etf_prices[asset_id] = (
                                    Price(FVal(price_info['price'])), 
                                    int(price_info['timestamp'])
                                )
                                # Also ensure it's in the general custom asset prices
                                Inquirer._custom_asset_prices[asset_id] = Price(FVal(price_info['price']))
                            elif isinstance(price_info, (int, float)):
                                # Handle legacy format
                                Inquirer._stock_etf_prices[asset_id] = (
                                    Price(FVal(price_info)), 
                                    0  # No timestamp, use 0
                                )
                                # Also ensure it's in the general custom asset prices
                                Inquirer._custom_asset_prices[asset_id] = Price(FVal(price_info))
                        
                        log.info(f"Loaded {len(stock_data)} stock/ETF prices from special disk cache")
                    except Exception as e:
                        log.error(f"Failed to load stock/ETF prices from {stock_etf_file}: {e}")
                else:
                    log.debug(f"No stock/ETF price cache file found at {stock_etf_file}")
                    
                # Log the total number of custom asset prices loaded
                total_prices = len(Inquirer._custom_asset_prices)
                if total_prices > 0:
                    log.info(f"Total custom asset prices loaded: {total_prices}")
        except Exception as e:
            # Non-fatal if we can't load from disk
            log.error(f"Could not load custom asset prices from disk: {e}")

    @classmethod
    def initialize_price_cache(cls) -> None:
        """Initialize the price cache - including loading custom asset prices from disk."""
        cls._initialize_custom_asset_prices()
        
        # Log how many stock/ETF prices we loaded
        stock_etf_count = len(cls._stock_etf_prices)
        custom_asset_count = len(cls._custom_asset_prices)
        
        if custom_asset_count > 0:
            log.info(f"Loaded {custom_asset_count} custom asset prices from persistent storage")
            # Log the first few for debugging
            max_to_show = min(5, custom_asset_count)
            shown = 0
            for asset_id, price in cls._custom_asset_prices.items():
                if shown < max_to_show:
                    log.debug(
                        f"Loaded custom asset price",
                        asset=asset_id,
                        price=price
                    )
                    shown += 1
        
        if stock_etf_count > 0:
            log.info(f"Loaded {stock_etf_count} stock/ETF prices with timestamps from persistent storage")
            # Log the first few for debugging
            max_to_show = min(5, stock_etf_count)
            shown = 0
            for asset_id, (price, timestamp) in cls._stock_etf_prices.items():
                if shown < max_to_show:
                    age_hours = (ts_now() - timestamp) / 3600 if timestamp > 0 else "unknown"
                    log.debug(
                        f"Loaded stock/ETF price",
                        asset=asset_id,
                        price=price,
                        age_hours=age_hours
                    )
                    shown += 1

    @staticmethod
    def _get_custom_asset_price(asset: Asset) -> Price | None:
        """Get a custom asset price from our persistent storage.
        
        Args:
            asset: The asset to get the price for
            
        Returns:
            The stored price or None if not found
        """
        if hasattr(asset, 'identifier'):
            # First check if this is a stock/ETF and we have a recent price
            try:
                if hasattr(asset, 'get_asset_type') and asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                    custom_asset = asset.resolve()
                    if (isinstance(custom_asset, CustomAsset) and 
                        hasattr(custom_asset, 'custom_asset_type') and 
                        custom_asset.custom_asset_type.lower() in ('stock', 'etf')):
                        
                        # Check if we have a price in the stock/ETF specific storage
                        if asset.identifier in Inquirer._stock_etf_prices:
                            price, timestamp = Inquirer._stock_etf_prices[asset.identifier]
                            age_in_hours = (ts_now() - timestamp) / 3600
                            
                            log.debug(
                                f"Found stock/ETF price in special cache",
                                asset=asset.identifier,
                                price=price,
                                age_hours=age_in_hours
                            )
                            
                            # Always return the cached price - we'll update it in background if needed
                            return price
            except Exception as e:
                log.debug(f"Error checking stock/ETF cache: {e}")
            
            # Fall back to regular custom asset price cache
            if asset.identifier in Inquirer._custom_asset_prices:
                price = Inquirer._custom_asset_prices[asset.identifier]
                log.debug(
                    f"Retrieved persistent price for custom asset",
                    asset=asset.identifier,
                    price=price
                )
                return price
        return None

    @staticmethod
    def _should_refresh_stock_price(asset: Asset) -> bool:
        """Determine if we should attempt to refresh a stock/ETF price.
        
        We use cached prices for stocks/ETFs but periodically refresh them to ensure
        they're reasonably up-to-date.
        
        Args:
            asset: The asset to check
            
        Returns:
            True if we should attempt a fresh price query, False to use cached price
        """
        if not hasattr(asset, 'identifier'):
            return True
            
        # If we don't have a cached price, we should definitely refresh
        if asset.identifier not in Inquirer._stock_etf_prices:
            return True
            
        # Check how old our cached price is
        price, timestamp = Inquirer._stock_etf_prices[asset.identifier]
        
        # Market hours logic - don't refresh too frequently outside market hours
        current_time = ts_now()
        age_in_seconds = current_time - timestamp
        
        # If price is less than 1 hour old, don't refresh
        if age_in_seconds < 3600:  # 1 hour in seconds
            return False
            
        # If price is less than 12 hours old, refresh with 25% probability
        if age_in_seconds < 43200 and random.random() > 0.25:  # 12 hours in seconds
            return False
            
        # If price is less than 1 day old, refresh with 50% probability  
        if age_in_seconds < 86400 and random.random() > 0.5:  # 24 hours in seconds
            return False
            
        # If price is less than 3 days old, refresh with 75% probability
        if age_in_seconds < 259200 and random.random() > 0.75:  # 3 days in seconds
            return False
            
        # Always refresh if price is more than 3 days old
        return True

    @staticmethod
    def _handle_custom_asset_price(asset: Asset) -> tuple[bool, Price]:
        """Special handler for custom assets (stocks/ETFs and other types like cars)
        
        Args:
            asset: The asset to check and possibly handle
            
        Returns:
            A tuple of (was_handled, price)
            was_handled is True if this was a custom asset and we tried to handle it
            price is the price if we successfully got it, or ZERO_PRICE otherwise
        """
        # First check if we have a stored price for this asset
        if hasattr(asset, 'identifier'):
            # Check directly in the _custom_asset_prices dictionary first
            if asset.identifier in Inquirer._custom_asset_prices:
                stored_price = Inquirer._custom_asset_prices[asset.identifier]
                if stored_price != ZERO_PRICE:
                    log.debug(
                        f"Using price from _custom_asset_prices dictionary in _handle_custom_asset_price",
                        asset=asset.identifier,
                        price=stored_price
                    )
                    return True, stored_price
            
            # Then check using the _get_custom_asset_price method
            stored_price = Inquirer._get_custom_asset_price(asset)
            if stored_price is not None and stored_price != ZERO_PRICE:
                # We have a stored price, use it
                
                # For stock/ETF assets, we'll check if we should attempt a refresh
                try:
                    if hasattr(asset, 'get_asset_type') and asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                        custom_asset = asset.resolve()
                        if (isinstance(custom_asset, CustomAsset) and 
                            hasattr(custom_asset, 'custom_asset_type') and 
                            custom_asset.custom_asset_type.lower() in ('stock', 'etf')):
                            
                            # Check if we should attempt to refresh
                            if Inquirer._should_refresh_stock_price(asset):
                                log.debug(
                                    f'Attempting to refresh stock/ETF price in background',
                                    asset=asset.identifier
                                )
                                
                                # Start a thread to update the price in the background
                                # This way we don't block the UI or other operations
                                try:
                                    import threading
                                    
                                    def update_price_bg():
                                        try:
                                            yahoo = Inquirer()._yahoofinance
                                            if yahoo:
                                                price = yahoo.query_custom_asset_price(
                                                    custom_asset=custom_asset,
                                                    to_currency='USD'
                                                )
                                                
                                                if price != ZERO_PRICE:
                                                    log.info(
                                                        f'Successfully updated stock/ETF price in background',
                                                        asset=asset.identifier,
                                                        price=price
                                                    )
                                                    # Store the updated price
                                                    Inquirer._store_custom_asset_price(asset, price)
                                        except Exception as e:
                                            log.debug(
                                                f'Background price update failed',
                                                asset=asset.identifier,
                                                error=str(e)
                                            )
                                    
                                    # Start the background thread
                                    thread = threading.Thread(target=update_price_bg)
                                    thread.daemon = True
                                    thread.start()
                                except Exception as e:
                                    log.debug(f"Failed to start background thread: {e}")
                        else:
                            # This is a non-stock/ETF custom asset (like a car)
                            # We should still mark it as handled to preserve its value
                            log.debug(
                                f'Using stored price for non-stock/ETF custom asset',
                                asset=asset.identifier,
                                name=getattr(custom_asset, 'name', 'unknown'),
                                asset_type=getattr(custom_asset, 'custom_asset_type', 'unknown'),
                                price=stored_price
                            )
                except Exception as e:
                    log.debug(f"Error checking if asset is stock/ETF for refresh: {e}")
                
                # Always return the stored price regardless of refresh attempts
                return True, stored_price
        
        try:
            if hasattr(asset, 'get_asset_type') and asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                try:
                    custom_asset = asset.resolve()
                    if isinstance(custom_asset, CustomAsset):
                        # Check if this is a stock/ETF type custom asset
                        if (hasattr(custom_asset, 'custom_asset_type') and 
                            custom_asset.custom_asset_type.lower() in ('stock', 'etf')):
                            
                            # Use Yahoo Finance directly for stock/ETF custom assets
                            yahoo = Inquirer()._yahoofinance
                            if yahoo:
                                log.debug(
                                    f'Direct Yahoo Finance lookup for stock/ETF custom asset',
                                    asset=custom_asset.identifier,
                                    name=getattr(custom_asset, 'name', 'unknown'),
                                    asset_type=custom_asset.custom_asset_type
                                )
                                
                                # Try up to 3 times with small delays between attempts
                                price = ZERO_PRICE
                                retry_count = 0
                                max_retries = 3
                                while price == ZERO_PRICE and retry_count < max_retries:
                                    price = yahoo.query_custom_asset_price(
                                        custom_asset=custom_asset,
                                        to_currency='USD'
                                    )
                                    
                                    if price != ZERO_PRICE:
                                        # Success!
                                        break
                                        
                                    # Increment retry counter and wait a bit
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        log.debug(
                                            f'Retrying Yahoo Finance lookup after zero price (attempt {retry_count}/{max_retries})',
                                            asset=custom_asset.identifier
                                        )
                                        time.sleep(1)  # Wait 1 second before retry
                                
                                if price != ZERO_PRICE:
                                    log.info(
                                        f'Successfully fetched Yahoo Finance price for {custom_asset.name}',
                                        price=price
                                    )
                                    # Add a special cache entry to prevent overrides
                                    Inquirer.set_cached_price(
                                        cache_key=(asset, A_USD),
                                        cached_price=CachedPriceEntry(
                                            price=price,
                                            time=ts_now(),
                                            oracle=CurrentPriceOracle.YAHOOFINANCE,
                                        ),
                                    )
                                    # Store in our persistent storage
                                    Inquirer._store_custom_asset_price(asset, price)
                                    return True, price
                                else:
                                    log.warning(
                                        f'Yahoo Finance returned zero price for {custom_asset.name} after {max_retries} attempts'
                                    )
                                    # Check if we have a previously stored price
                                    stored_price = Inquirer._get_custom_asset_price(asset)
                                    if stored_price is not None and stored_price != ZERO_PRICE:
                                        log.info(
                                            f'Using previously stored price for {custom_asset.name} despite failed Yahoo query',
                                            price=stored_price
                                        )
                                        return True, stored_price
                                    
                                    # Still mark as handled to prevent overriding with zero
                                    return True, ZERO_PRICE
                        else:
                            # This is a non-stock/ETF custom asset (like a car)
                            # We should mark it as handled to prevent it from being processed by other oracles
                            log.debug(
                                f'Handling non-stock/ETF custom asset',
                                asset=custom_asset.identifier,
                                name=getattr(custom_asset, 'name', 'unknown'),
                                asset_type=getattr(custom_asset, 'custom_asset_type', 'unknown')
                            )
                            
                            # Check if we have a previously stored price
                            stored_price = Inquirer._get_custom_asset_price(asset)
                            if stored_price is not None and stored_price != ZERO_PRICE:
                                log.info(
                                    f'Using previously stored price for custom asset',
                                    asset=custom_asset.identifier,
                                    price=stored_price
                                )
                                return True, stored_price
                            
                            # Also check directly in the _custom_asset_prices dictionary
                            if hasattr(asset, 'identifier') and asset.identifier in Inquirer._custom_asset_prices:
                                stored_price = Inquirer._custom_asset_prices[asset.identifier]
                                log.info(
                                    f'Using price from _custom_asset_prices dictionary for custom asset',
                                    asset=custom_asset.identifier,
                                    price=stored_price
                                )
                                return True, stored_price
                            
                            # Mark as handled but return ZERO_PRICE if no stored price
                            # This prevents other oracles from trying to handle it
                            return True, ZERO_PRICE
                except Exception as e:
                    log.error(
                        f'Error handling custom asset',
                        asset=getattr(asset, 'identifier', 'unknown'),
                        error=str(e)
                    )
                    # Check if we have a previously stored price
                    stored_price = Inquirer._get_custom_asset_price(asset)
                    if stored_price is not None and stored_price != ZERO_PRICE:
                        log.info(
                            f'Using previously stored price despite error',
                            asset=getattr(asset, 'identifier', 'unknown'),
                            price=stored_price
                        )
                        return True, stored_price
                    
                    # Also check directly in the _custom_asset_prices dictionary
                    if hasattr(asset, 'identifier') and asset.identifier in Inquirer._custom_asset_prices:
                        stored_price = Inquirer._custom_asset_prices[asset.identifier]
                        log.info(
                            f'Using price from _custom_asset_prices dictionary despite error',
                            asset=getattr(asset, 'identifier', 'unknown'),
                            price=stored_price
                        )
                        return True, stored_price
                        
                    # Still mark as handled to prevent overriding with zero
                    return True, ZERO_PRICE
        except Exception:
            # Not a custom asset or other error
            pass
            
        # Not handled
        return False, ZERO_PRICE

    @staticmethod
    def find_usd_price(
            asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> Price:
        """Wrapper for find_usd_prices to get the usd price of a single asset."""
        # For custom assets, we need maximum protection to preserve their values
        try:
            if hasattr(asset, 'get_asset_type') and asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                # Check if this is a custom asset
                custom_asset = asset.resolve()
                if isinstance(custom_asset, CustomAsset):
                    asset_type = getattr(custom_asset, 'custom_asset_type', 'unknown').lower()
                    is_stock_etf = asset_type in ('stock', 'etf')
                    
                    log.debug(
                        f"Custom asset direct handling in find_usd_price",
                        asset=asset.identifier,
                        name=getattr(custom_asset, 'name', 'unknown'),
                        asset_type=asset_type,
                        ignore_cache_setting=ignore_cache
                    )
                    
                    # First check directly in the _custom_asset_prices dictionary
                    if hasattr(asset, 'identifier') and asset.identifier in Inquirer._custom_asset_prices:
                        stored_price = Inquirer._custom_asset_prices[asset.identifier]
                        if stored_price != ZERO_PRICE:
                            log.debug(
                                f"Using price from _custom_asset_prices dictionary in find_usd_price",
                                asset=asset.identifier,
                                price=stored_price
                            )
                            return stored_price
                    
                    # Then check using the _get_custom_asset_price method
                    stored_price = Inquirer._get_custom_asset_price(asset)
                    if stored_price is not None and stored_price != ZERO_PRICE:
                        log.debug(
                            f"Using cached price for custom asset",
                            asset=asset.identifier,
                            price=stored_price,
                            asset_type=asset_type
                        )
                        
                        # If ignore_cache was requested and this is a stock/ETF, trigger a refresh in the background
                        # but still use cached price
                        if ignore_cache and is_stock_etf:
                            try:
                                import threading
                                
                                def refresh_bg():
                                    try:
                                        # Small delay to avoid hammering API
                                        time.sleep(0.5)
                                        yahoo = Inquirer()._yahoofinance
                                        if yahoo:
                                            new_price = yahoo.query_custom_asset_price(
                                                custom_asset=custom_asset,
                                                to_currency='USD'
                                            )
                                            
                                            if new_price != ZERO_PRICE:
                                                log.info(
                                                    f'Successfully refreshed stock/ETF price in background',
                                                    asset=asset.identifier,
                                                    price=new_price
                                                )
                                                # Store the updated price
                                                Inquirer._store_custom_asset_price(asset, new_price)
                                    except Exception as e:
                                        log.debug(
                                            f'Background price refresh failed',
                                            asset=asset.identifier,
                                            error=str(e)
                                        )
                                
                                # Start background thread
                                thread = threading.Thread(target=refresh_bg)
                                thread.daemon = True
                                thread.start()
                            except Exception as e:
                                log.debug(f"Failed to start background thread: {e}")
                        
                        # Always return the cached value for any custom asset
                        return stored_price
                    
        except Exception as e:
            log.debug(
                f"Error in custom asset price detection, continuing with normal flow",
                asset=getattr(asset, 'identifier', 'unknown'),
                error=str(e)
            )
            
        # Standard handling for custom assets or if no cached price was found
        was_handled, price = Inquirer._handle_custom_asset_price(asset)
        if was_handled and price != ZERO_PRICE:
            return price
            
        # Fall back to normal flow for other assets
        return Inquirer.find_usd_prices(
            assets=[asset],
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        ).get(asset, ZERO_PRICE)

    @staticmethod
    def find_usd_prices(
            assets: list[Asset],
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, Price]:
        """Wrapper for find_prices to get usd prices."""
        # Direct handler for custom assets (both stocks/ETFs and other types like cars)
        # This is a non-intrusive addition that handles custom assets first
        result_prices = {}
        stock_etf_assets = []
        other_custom_assets = []
        non_custom_assets = []
        
        # Log if this is a refresh operation
        if ignore_cache:
            log.debug(f"Processing find_usd_prices with ignore_cache=True for {len(assets)} assets")
        
        # First separate custom assets from other assets
        for asset in assets:
            try:
                if hasattr(asset, 'get_asset_type') and asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                    try:
                        custom_asset = asset.resolve()
                        if isinstance(custom_asset, CustomAsset):
                            asset_type = getattr(custom_asset, 'custom_asset_type', 'unknown').lower()
                            if asset_type in ('stock', 'etf'):
                                # This is a stock/ETF custom asset
                                stock_etf_assets.append(asset)
                            else:
                                # This is another type of custom asset (like a car)
                                other_custom_assets.append(asset)
                            continue
                    except Exception:
                        pass
            except Exception:
                pass
                
            # Not a custom asset
            non_custom_assets.append(asset)
        
        if ignore_cache:
            if stock_etf_assets:
                log.info(f"Refresh prices requested for {len(stock_etf_assets)} stock/ETF assets - will use cached values and refresh in background")
            if other_custom_assets:
                log.info(f"Refresh prices requested for {len(other_custom_assets)} other custom assets - will preserve their values")
        
        # Process stock/ETF custom assets - ALWAYS use cached values first, regardless of ignore_cache setting
        for asset in stock_etf_assets:
            # First check directly in the _custom_asset_prices dictionary
            if hasattr(asset, 'identifier') and asset.identifier in Inquirer._custom_asset_prices:
                stored_price = Inquirer._custom_asset_prices[asset.identifier]
                if stored_price != ZERO_PRICE:
                    result_prices[asset] = stored_price
                    log.debug(
                        f"Using price from _custom_asset_prices dictionary for stock/ETF",
                        asset=asset.identifier,
                        price=stored_price
                    )
                    continue
            
            # Then check using the _get_custom_asset_price method
            stored_price = Inquirer._get_custom_asset_price(asset)
            if stored_price is not None and stored_price != ZERO_PRICE:
                # We have a stored price, use it
                result_prices[asset] = stored_price
                
                # Now check if we should trigger a background refresh based on age
                try:
                    if ignore_cache or Inquirer._should_refresh_stock_price(asset):
                        # Trigger background refresh
                        try:
                            import threading
                            
                            def update_price_bg(refresh_asset):
                                try:
                                    custom_asset = refresh_asset.resolve()
                                    yahoo = Inquirer()._yahoofinance
                                    if yahoo:
                                        price = yahoo.query_custom_asset_price(
                                            custom_asset=custom_asset,
                                            to_currency='USD'
                                        )
                                        
                                        if price != ZERO_PRICE:
                                            log.info(
                                                f'Successfully refreshed price in background',
                                                asset=refresh_asset.identifier,
                                                price=price
                                            )
                                            # Store the updated price
                                            Inquirer._store_custom_asset_price(refresh_asset, price)
                                except Exception as e:
                                    log.debug(
                                        f'Background price update failed',
                                        asset=getattr(refresh_asset, 'identifier', 'unknown'),
                                        error=str(e)
                                    )
                            
                            # Start the background thread
                            thread = threading.Thread(target=update_price_bg, args=(asset,))
                            thread.daemon = True
                            thread.start()
                        except Exception as e:
                            log.debug(f"Failed to start background thread: {e}")
                except Exception as e:
                    log.debug(f"Error checking if asset is stock/ETF for refresh: {e}")
                
                # Always continue to next asset - we've already added this one
                continue
                
            # No stored price found, try to get a price directly
            # This should be rare, only for first-time access
            was_handled, price = Inquirer._handle_custom_asset_price(asset)
            if price != ZERO_PRICE:
                result_prices[asset] = price
            else:
                # Add to non-custom assets if we couldn't get a price
                non_custom_assets.append(asset)
                
            # Add a small delay to avoid rate limiting
            if len(stock_etf_assets) > 1:
                time.sleep(0.5)
        
        # Process other custom assets (like cars) - ALWAYS preserve their values
        for asset in other_custom_assets:
            # First check directly in the _custom_asset_prices dictionary
            if hasattr(asset, 'identifier') and asset.identifier in Inquirer._custom_asset_prices:
                stored_price = Inquirer._custom_asset_prices[asset.identifier]
                if stored_price != ZERO_PRICE:
                    result_prices[asset] = stored_price
                    log.debug(
                        f"Using price from _custom_asset_prices dictionary for custom asset",
                        asset=asset.identifier,
                        price=stored_price
                    )
                    continue
            
            # Then check using the _get_custom_asset_price method
            stored_price = Inquirer._get_custom_asset_price(asset)
            if stored_price is not None and stored_price != ZERO_PRICE:
                # We have a stored price, use it
                result_prices[asset] = stored_price
                log.debug(
                    f"Using stored price for custom asset",
                    asset=asset.identifier,
                    price=stored_price
                )
                continue
                
            # No stored price found, try to handle it
            was_handled, price = Inquirer._handle_custom_asset_price(asset)
            if price != ZERO_PRICE:
                result_prices[asset] = price
            else:
                # Add to non-custom assets if we couldn't get a price
                non_custom_assets.append(asset)
        
        # Process all non-custom assets with normal flow
        if non_custom_assets:
            log.debug(f"Processing {len(non_custom_assets)} non-custom assets with standard flow")
            normal_prices = Inquirer.find_prices(
                from_assets=non_custom_assets,
                to_asset=A_USD,
                ignore_cache=ignore_cache,
                skip_onchain=skip_onchain,
            )
            # Merge the results
            result_prices.update(normal_prices)
        
        # Debug the final results
        if ignore_cache:
            log.info(f"Completed price refresh for {len(assets)} assets ({len(result_prices)} with prices)")
            
        # Detailed debugging for custom assets
        for asset, price in result_prices.items():
            if hasattr(asset, 'get_asset_type') and asset.get_asset_type() == AssetType.CUSTOM_ASSET:
                try:
                    custom_asset = asset.resolve()
                    if isinstance(custom_asset, CustomAsset):
                        asset_type = getattr(custom_asset, 'custom_asset_type', 'unknown')
                        log.debug(
                            f"Final price for custom asset",
                            asset=asset.identifier,
                            name=getattr(custom_asset, 'name', 'unknown'),
                            asset_type=asset_type,
                            price=price
                        )
                except Exception:
                    pass
            
        return result_prices

    @staticmethod
    def find_usd_price_and_oracle(
            asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> tuple[Price, CurrentPriceOracle]:
        """Wrapper for find_usd_prices_and_oracles to
        get the usd price and oracle for a single asset."""
        return Inquirer.find_usd_prices_and_oracles(
            assets=[asset],
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        ).get(asset, (ZERO_PRICE, CurrentPriceOracle.FIAT))

    @staticmethod
    def find_usd_prices_and_oracles(
            assets: list[Asset],
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, tuple[Price, CurrentPriceOracle]]:
        """Wrapper for _find_prices to get usd prices and oracles."""
        return Inquirer._find_prices(
            from_assets=assets,
            to_asset=A_USD,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        )

    def find_lp_price_from_uniswaplike_pool(self, token: EvmToken) -> Price | None:
        """Calculates the price for a uniswaplike LP token the contract of which is also
        the contract of the pool it represents. For example uniswap or velodrome LP tokens."""
        return lp_price_from_uniswaplike_pool_contract(
            evm_inquirer=self.get_evm_manager(token.chain_id).node_inquirer,  # get the inquirer for the chain the token is in  # noqa: E501
            token=token,
            token_price_func=self.find_usd_price,
            token_price_func_args=[],
            block_identifier='latest',
        )

    def find_curve_pool_price(self, lp_token: EvmToken) -> Price | None:
        """
        1. Obtain the pool for this token
        2. Obtain total supply of lp tokens
        3. Obtain value (in USD) for all assets in the pool
        4. Calculate the price for an LP token

        logic source: https://medium.com/coinmonks/the-joys-of-valuing-curve-lp-tokens-4e4a148eaeb9

        Returns the price of 1 LP token from the pool

        May raise:
        - RemoteError
        """
        assert lp_token.chain_id in CURVE_CHAIN_IDS, f'{lp_token} is not on a curve supported chain'  # noqa: E501
        chain_id = cast('CURVE_CHAIN_ID_TYPE', lp_token.chain_id)
        evm_manager = self.get_evm_manager(chain_id=chain_id)
        evm_manager.assure_curve_cache_is_queried_and_decoder_updated(
            node_inquirer=evm_manager.node_inquirer,
            transactions_decoder=evm_manager.transactions_decoder,
        )

        with GlobalDBHandler().conn.read_ctx() as cursor:
            pool_address_in_cache = globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.CURVE_POOL_ADDRESS, str(chain_id.serialize_for_db()), lp_token.evm_address),  # noqa: E501
            )
            if pool_address_in_cache is None:
                return None
            # pool address is guaranteed to be checksummed due to how we save it
            pool_address = string_to_evm_address(pool_address_in_cache)
            pool_tokens_addresses = read_curve_pool_tokens(
                cursor=cursor,
                pool_address=pool_address,
                chain_id=chain_id,
            )

        tokens: list[EvmToken] = []
        try:  # Translate addresses to tokens
            for token_address_str in pool_tokens_addresses:
                token_address = string_to_evm_address(token_address_str)
                if token_address == ETH_SPECIAL_ADDRESS:
                    tokens.append(self.weth)
                else:
                    tokens.append(EvmToken(evm_address_to_identifier(
                        address=token_address,
                        chain_id=chain_id,
                        token_type=EvmTokenKind.ERC20,
                    )))
        except UnknownAsset:
            return None

        # Get price for each token in the pool
        prices = []
        for token in tokens:
            price = self.find_usd_price(token)
            if price == ZERO_PRICE:
                log.error(
                    f'Could not calculate price for {lp_token} due to inability to '
                    f'fetch price for {token}.',
                )
                return None
            prices.append(price)

        # Query total supply of the LP token
        contract = EvmContract(
            address=lp_token.evm_address,
            abi=evm_manager.node_inquirer.contracts.abi('ERC20_TOKEN'),
            deployed_block=0,
        )
        total_supply = contract.call(
            node_inquirer=evm_manager.node_inquirer,
            method_name='totalSupply',
        )

        # Query balances for each token in the pool
        contract = EvmContract(
            address=pool_address,
            abi=evm_manager.node_inquirer.contracts.abi('CURVE_POOL'),
            deployed_block=0,
        )
        calls = [
            (pool_address, contract.encode(method_name='balances', arguments=[i]))
            for i in range(len(tokens))
        ]
        output = evm_manager.node_inquirer.multicall_2(
            require_success=False,
            calls=calls,
        )

        # Check that the output has the correct structure
        if not all(len(call_result) == 2 for call_result in output):
            log.debug(
                f'Failed to query contract methods while finding curve pool price. '
                f'Not every outcome has length 2. {output}',
            )
            return None
        # Check that all the requests were successful
        if not all(contract_output[0] for contract_output in output):
            log.debug(f'Failed to query contract methods while finding curve price. {output}')
            return None
        # Deserialize information obtained in the multicall execution
        data = []
        for i, token in enumerate(tokens):
            amount_decoded = contract.decode(output[i][1], 'balances', arguments=[i])
            if not _check_curve_contract_call(amount_decoded):
                log.debug(f'Failed to decode balances {i} while finding curve price. {output}')
                return None
            # https://github.com/PyCQA/pylint/issues/4739
            amount = amount_decoded[0]
            normalized_amount = token_normalized_value_decimals(amount, token.decimals)
            data.append(normalized_amount)

        # Prices and data should verify this relation for the following operations
        if len(prices) != len(data):
            log.debug(
                f'Length of prices {len(prices)} does not match len of data {len(data)} '
                f'while querying curve pool price.',
            )
            return None
        # Total number of assets price in the pool
        total_assets_value = sum(map(operator.mul, data, prices))
        if total_assets_value == 0:
            log.error(
                f'Curve pool price returned unexpected data {data} that lead to a zero price.',
            )
            return None

        return (total_assets_value / total_supply) * (10 ** lp_token.get_decimals())

    def find_gearbox_price(self, token: EvmToken) -> Price | None:
        node_inquirer = self.get_evm_manager(chain_id=token.chain_id).node_inquirer
        underlying_token = None
        farming_tokens = {token.farming_pool_token for token in read_gearbox_data_from_cache(token.chain_id)[0].values()}  # noqa: E501
        if token in farming_tokens:
            farming_contract = EvmContract(
                address=token.evm_address,
                abi=node_inquirer.contracts.abi('GEARBOX_FARMING_POOL'),
                deployed_block=0,  # not used here
            )
            try:
                lp_token = farming_contract.call(node_inquirer=node_inquirer, method_name='stakingToken')  # noqa: E501
                lp_token = deserialize_evm_address(lp_token)
            except (RemoteError, BlockchainQueryError, DeserializationError) as e:
                log.error(f'Failed to query stakingToken method in {node_inquirer.chain_name} Gearbox Pool {token.evm_address}. {e!s}')  # noqa: E501
                return None
        else:
            lp_token = token.evm_address

        with GlobalDBHandler().conn.read_ctx() as cursor:
            maybe_underlying_tokens = GlobalDBHandler.fetch_underlying_tokens(
                cursor=cursor,
                parent_token_identifier=token.identifier,
            )
        lp_contract = EvmContract(
            address=lp_token,
            abi=node_inquirer.contracts.abi('GEARBOX_LP'),
            deployed_block=0,  # not used here
        )
        # check if the underlying token is in the DB, otherwise query the chain
        # and store it in the DB and use it
        if maybe_underlying_tokens is None or len(maybe_underlying_tokens) != 1:
            if (
                underlying_token := ensure_gearbox_lp_underlying_tokens(
                    token_identifier=token.identifier,
                    node_inquirer=node_inquirer,
                    lp_contract=lp_contract,
                )
            ) is None:
                log.error(f'Failed to query underlying tokens of {node_inquirer.chain_name} {token.evm_address} Gearbox pool.')  # noqa: E501
                return None
        else:  # Use the existing underlying token by converting its address to a Token
            underlying_token = EvmToken(
                evm_address_to_identifier(
                    address=maybe_underlying_tokens[0].address,
                    chain_id=token.chain_id,
                    token_type=EvmTokenKind.ERC20,
                ),
            )

        try:
            price_per_share = lp_contract.call(
                node_inquirer=node_inquirer,
                method_name='convertToAssets',
                arguments=[10 ** (decimals := token.get_decimals())],
            )
        except (RemoteError, BlockchainQueryError) as e:
            log.error(f'Failed to query convertToAssets method in {node_inquirer.chain_name} Gearbox pool {lp_token}. {e!s}')  # noqa: E501
        else:
            underlying_token_price = self.find_usd_price(underlying_token)
            if underlying_token_price == ZERO_PRICE:
                log.error(f'Could not calculate price for {node_inquirer.chain_name} {lp_token} due to inability to fetch price for {underlying_token.identifier}.')  # noqa: E501
                return None
            return Price(price_per_share * underlying_token_price / 10 ** decimals)

        return None

    def find_yearn_price(
            self,
            token: EvmToken,
            vault_abi: Literal['YEARN_VAULT_V3', 'YEARN_VAULT_V2'],
    ) -> Price | None:
        """
        Query price for a yearn vault v2 or v3 token using the pricePerShare method
        and the price of the underlying token.
        """
        ethereum = self.get_evm_manager(chain_id=ChainID.ETHEREUM)
        globaldb = GlobalDBHandler()
        with globaldb.conn.read_ctx() as cursor:
            maybe_underlying_tokens = globaldb.fetch_underlying_tokens(cursor, ethaddress_to_identifier(token.evm_address))  # noqa: E501

        contract = EvmContract(
            address=token.evm_address,
            abi=ethereum.node_inquirer.contracts.abi(vault_abi),
            deployed_block=0,
        )
        if maybe_underlying_tokens is None or len(maybe_underlying_tokens) != 1:
            # underlying token not recorded in the DB. Ask the chain
            try:
                remote_underlying_token = contract.call(ethereum.node_inquirer, 'token')
            except (RemoteError, BlockchainQueryError) as e:
                log.error(f'Failed to query underlying token method in Yearn v2 Vault. {e!s}')
                return None

            try:
                underlying_token_address = deserialize_evm_address(remote_underlying_token)
            except DeserializationError:
                log.error(f'underlying token call of {token.evm_address} returned invalid address {remote_underlying_token}')  # noqa: E501
                return None

            try:  # make sure it's in the global DB
                underlying_token = get_or_create_evm_token(
                    userdb=ethereum.node_inquirer.database,
                    evm_address=underlying_token_address,
                    chain_id=ChainID.ETHEREUM,
                    encounter=TokenEncounterInfo(
                        description='Detecting Yearn vault underlying tokens',
                    ),
                )
            except NotERC20Conformant as e:
                log.error(
                    f'Error fetching ethereum token {underlying_token_address} while '
                    f'detecting underlying tokens of {token.evm_address!s}: {e!s}',
                )
                return None

            # store it in the DB, so next time no need to query chain
            with globaldb.conn.write_ctx() as write_cursor:
                try:
                    globaldb._add_underlying_tokens(
                        write_cursor=write_cursor,
                        parent_token_identifier=token.identifier,
                        underlying_tokens=[
                            UnderlyingToken(
                                address=underlying_token_address,
                                token_kind=EvmTokenKind.ERC20,  # this may be a guess here
                                weight=ONE,  # all yearn vaults have single underlying
                            )],
                        chain_id=ChainID.ETHEREUM,
                    )
                except InputError as e:
                    log.error(f'Failed to add yearn underlying token {underlying_token_address} for {token.identifier} due to: {e}')  # noqa: E501
                    return None
        else:
            underlying_token = EvmToken(ethaddress_to_identifier(maybe_underlying_tokens[0].address))  # noqa: E501

        underlying_token_price = self.find_usd_price(underlying_token)
        # Get the price per share from the yearn contract
        contract = EvmContract(
            address=token.evm_address,
            abi=ethereum.node_inquirer.contracts.abi(vault_abi),
            deployed_block=0,
        )
        try:
            price_per_share = contract.call(ethereum.node_inquirer, 'pricePerShare')
        except (RemoteError, BlockchainQueryError) as e:
            log.error(f'Failed to query pricePerShare method for Yearn vault {token}. {e!s}')
        else:
            return Price(price_per_share * underlying_token_price / 10 ** token.get_decimals())

        return None

    def find_yearn_staking_price(self, token: EvmToken) -> Price | None:
        """Find prices for staked yearn tokens
        Those tokens are confirmed to be 1:1 with the underlying token.
        There are 3 types of vaults reported by the API but all of them respect
        the proportion 1:1.

        The tokens representing staked yearn vaults have the protocol `YEARN_STAKING_PROTOCOL`
        and as underlying token they have a Yearn Vault token. The information is populated
        by calling the yearn API. Until the yearn vault api cache creation runs the price is
        not reliable.
        """
        if (
            token.underlying_tokens is None or
            len(token.underlying_tokens) == 0 or
            token.protocol != YEARN_STAKING_PROTOCOL
        ):
            log.error(f'Logic to query staked yearn vault price with a malformed token {token}')
            return None

        try:
            vault = EvmToken(evm_address_to_identifier(
                address=token.underlying_tokens[0].address,
                chain_id=token.chain_id,
            ))
        except UnknownAsset:
            log.error(f'Unknown vault for yearn staked token {token}. {token.underlying_tokens[0].address=}')  # noqa: E501
            return None

        return get_underlying_asset_price(vault)[0]

    def find_hop_lp_price(self, lp_token: EvmToken) -> Price | None:
        """Returns the price of a hop lp token fetched from the pool contract"""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            if (amm_address := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(
                    CacheType.HOP_POOL_ADDRESS,
                    str(lp_token.chain_id.value),
                    lp_token.evm_address,
                ),
            )) is None:
                log.error(
                    f'Could not find the pool address of Hop LP token {lp_token.evm_address!s} on '
                    f'{lp_token.chain_id!s}. Skipping its price query',
                )
                return ZERO_PRICE

        # Query virtual price from the pool contract
        evm_manager = self.get_evm_manager(chain_id=lp_token.chain_id)
        contract = EvmContract(
            address=string_to_evm_address(amm_address),
            abi=evm_manager.node_inquirer.contracts.abi('HOP_POOL'),
            deployed_block=0,
        )
        try:
            # return price of pool_token * virtual price of lp_token
            return self.find_usd_price(Asset(evm_address_to_identifier(
                address=deserialize_evm_address(contract.call(
                    node_inquirer=evm_manager.node_inquirer,
                    method_name='getToken',
                    arguments=[0],
                )),
                chain_id=lp_token.chain_id,
                token_type=EvmTokenKind.ERC20,
            ))) * FVal(contract.call(
                node_inquirer=evm_manager.node_inquirer,
                method_name='getVirtualPrice',
            )) / 10 ** lp_token.get_decimals()
        except DeserializationError as e:
            log.error(f'Failed to deserialize Hop pool token address of {amm_address!s} in {evm_manager.node_inquirer.chain_name!s}. {e!s}')  # noqa: E501
            return ZERO_PRICE
        except RemoteError as e:
            log.error(f'Failed to query virtual price of Hop lp token {lp_token.evm_address!s} in {evm_manager.node_inquirer.chain_name!s}. {e!s}')  # noqa: E501
            return ZERO_PRICE

    @staticmethod
    def get_fiat_usd_exchange_rates(currencies: Iterable[FiatAsset]) -> dict[FiatAsset, Price]:
        """Gets the USD exchange rate of any of the given assets

        In case of failure to query a rate it's returned as zero"""
        instance = Inquirer()
        rates = {instance.usd: Price(ONE)}
        for currency in currencies:
            if (price_and_oracle := Inquirer()._query_fiat_pair(
                base=instance.usd,
                quote=currency,
            )) is not None:
                rates[currency], _ = price_and_oracle
            else:
                rates[currency] = ZERO_PRICE

        return rates

    @staticmethod
    def query_historical_fiat_exchange_rates(
            from_fiat_currency: FiatAsset,
            to_fiat_currency: FiatAsset,
            timestamp: Timestamp,
    ) -> Price | None:
        assert from_fiat_currency.is_fiat(), 'fiat currency should have been provided'
        assert to_fiat_currency.is_fiat(), 'fiat currency should have been provided'

        if from_fiat_currency == to_fiat_currency:
            return Price(ONE)

        # Check cache
        price_cache_entry = GlobalDBHandler.get_historical_price(
            from_asset=from_fiat_currency,
            to_asset=to_fiat_currency,
            timestamp=timestamp,
            max_seconds_distance=DAY_IN_SECONDS,
        )
        if price_cache_entry:
            return price_cache_entry.price

        try:
            prices_map = get_historical_xratescom_exchange_rates(
                from_asset=from_fiat_currency,
                time=timestamp,
            )
        except RemoteError:
            return None

        # Since xratecoms has daily rates let's save at timestamp of UTC day start
        timestamp = timestamp_to_daystart_timestamp(timestamp)
        for asset, asset_price in prices_map.items():
            GlobalDBHandler.add_historical_prices(entries=[HistoricalPrice(
                from_asset=from_fiat_currency,
                to_asset=asset,
                source=HistoricalPriceOracle.XRATESCOM,
                timestamp=timestamp,
                price=asset_price,
            )])
            if asset == to_fiat_currency:
                rate = asset_price
                break
        else:
            log.debug(
                f'Could not find historical fiat exchange rate for asset {to_fiat_currency=}',
            )
            return None

        log.debug('Historical fiat exchange rate query successful', rate=rate)
        return rate

    @staticmethod
    def _query_fiat_pairs(
            from_assets: list[Asset],
            to_asset: Asset,
    ) -> tuple[list[Asset], dict[Asset, tuple[Price, CurrentPriceOracle]]]:
        """If to_asset is fiat, query the current price for any fiat assets in from_assets.
        Returns a tuple containing a list of non fiat assets and a dict of prices found.
        """
        if not to_asset.is_fiat():
            return from_assets, {}

        non_fiat_assets, found_prices = [], {}
        for from_asset in from_assets:
            if (
                from_asset.is_fiat() and
                (price_and_oracle := Inquirer._query_fiat_pair(
                    base=from_asset.resolve_to_fiat_asset(),
                    quote=to_asset.resolve_to_fiat_asset(),
                )) is not None
            ):
                found_prices[from_asset] = price_and_oracle
                continue

            non_fiat_assets.append(from_asset)

        return non_fiat_assets, found_prices

    @staticmethod
    def _query_fiat_pair(
            base: FiatAsset,
            quote: FiatAsset,
    ) -> tuple[Price, CurrentPriceOracle] | None:
        """Queries the current price between two fiat assets.
        Returns a tuple containing the current price (or a cached price from within
        the last 30 days) and the oracle. Logs an error and returns None if no price can be found.
        """
        if base == quote:
            return Price(ONE), CurrentPriceOracle.FIAT

        now = ts_now()
        # Check cache for a price within the last 24 hrs
        price_cache_entry = GlobalDBHandler.get_historical_price(
            from_asset=base,
            to_asset=quote,
            timestamp=now,
            max_seconds_distance=DAY_IN_SECONDS,
        )
        if price_cache_entry:
            return price_cache_entry.price, CurrentPriceOracle.FIAT

        # Use the xratescom query and save all prices in the cache
        price = None
        with suppress(RemoteError):
            price_map = get_current_xratescom_exchange_rates(base)
            for quote_asset, quote_price in price_map.items():
                if quote_asset == quote:
                    # if the quote asset price is found return it
                    price = quote_price

                GlobalDBHandler.add_historical_prices(entries=[HistoricalPrice(
                    from_asset=base,
                    to_asset=quote_asset,
                    source=HistoricalPriceOracle.XRATESCOM,
                    timestamp=timestamp_to_daystart_timestamp(now),
                    price=quote_price,
                )])

            if price:  # the quote asset may not be found
                return price, CurrentPriceOracle.FIAT

        # Check cache
        price_cache_entry = GlobalDBHandler.get_historical_price(
            from_asset=base,
            to_asset=quote,
            timestamp=now,
            max_seconds_distance=MONTH_IN_SECONDS,
        )
        if price_cache_entry:
            log.debug(
                f'Could not query online apis for a fiat price. '
                f'Used cached value from '
                f'{(now - price_cache_entry.timestamp) / DAY_IN_SECONDS} days ago.',
                base_currency=base.identifier,
                quote_currency=quote.identifier,
                price=price_cache_entry.price,
            )
            return price_cache_entry.price, CurrentPriceOracle.FIAT

        # else
        log.error(f'Could not find a current {base.identifier} price for {quote.identifier}')
        return None

    @staticmethod
    def clear() -> None:
        """Cleans up the active price oracles.

        Oracles will no longer depend on the logged in user.
        If this function is called then set_oracles_order() should be called to
        re-activate the Inquirer.
        
        Also cleans up any custom caches that are not needed after the user logs out.
        """
        original_special_tokens = Inquirer.__instance.special_tokens if Inquirer.__instance else None
        
        # Clean up current oracles
        Inquirer.__instance = None
        # Reset attribute that is linked to the user that was logged in
        Inquirer._uniswapv2 = None
        Inquirer._uniswapv3 = None
        Inquirer._oracles = None
        Inquirer._oracle_instances = None
        Inquirer._oracles_not_onchain = None
        Inquirer._oracle_instances_not_onchain = None
        
        # Reset cached prices but keep persistent ones
        # We need to create a new instance with the original special tokens
        if original_special_tokens:
            Inquirer.__instance = Inquirer()
            Inquirer.__instance.special_tokens = original_special_tokens

    @staticmethod
    def force_refresh_stock_etf_prices() -> None:
        """Force refresh all stock/ETF prices.
        
        This is a helper method that can be called by the UI to force a refresh
        of all stock/ETF prices, typically after the user has noticed that
        some prices are stale or incorrect.
        
        This is done in the background to avoid blocking the UI.
        """
        import threading
        
        def refresh_all_stocks_bg():
            try:
                # Get all assets that are in the stock/ETF cache
                asset_ids = list(Inquirer._stock_etf_prices.keys())
                if not asset_ids:
                    log.debug("No stock/ETF assets found to refresh")
                    return
                    
                log.info(f"Starting background refresh of {len(asset_ids)} stock/ETF prices")
                
                # Load the assets
                from rotkehlchen.assets.asset import Asset
                assets_to_refresh = []
                for asset_id in asset_ids:
                    try:
                        asset = Asset(asset_id)
                        assets_to_refresh.append(asset)
                    except Exception as e:
                        log.error(
                            f"Failed to load asset for refresh",
                            asset_id=asset_id,
                            error=str(e)
                        )
                        
                # Process each asset
                yahoo = Inquirer()._yahoofinance
                if not yahoo:
                    log.error("Yahoo Finance oracle not available for stock refresh")
                    return
                    
                success_count = 0
                for idx, asset in enumerate(assets_to_refresh):
                    try:
                        custom_asset = asset.resolve()
                        if not (isinstance(custom_asset, CustomAsset) and 
                                hasattr(custom_asset, 'custom_asset_type') and 
                                custom_asset.custom_asset_type.lower() in ('stock', 'etf')):
                            log.debug(
                                f"Skipping non-stock/ETF asset in refresh",
                                asset=asset.identifier
                            )
                            continue
                            
                        log.debug(
                            f"Refreshing stock/ETF price ({idx+1}/{len(assets_to_refresh)})",
                            asset=asset.identifier,
                            name=getattr(custom_asset, 'name', 'unknown')
                        )
                        
                        price = yahoo.query_custom_asset_price(
                            custom_asset=custom_asset,
                            to_currency='USD'
                        )
                        
                        if price != ZERO_PRICE:
                            log.info(
                                f'Successfully refreshed price',
                                asset=asset.identifier,
                                name=getattr(custom_asset, 'name', 'unknown'),
                                price=price
                            )
                            # Store the updated price
                            Inquirer._store_custom_asset_price(asset, price)
                            success_count += 1
                        else:
                            log.warning(
                                f'Yahoo Finance returned zero price for {asset.identifier}'
                            )
                            
                        # Add a small delay to avoid rate limiting
                        time.sleep(0.5)
                        
                    except Exception as e:
                        log.error(
                            f'Failed to refresh stock/ETF price',
                            asset=getattr(asset, 'identifier', 'unknown'),
                            error=str(e)
                        )
                        
                log.info(f"Completed background refresh of stock/ETF prices. Updated {success_count}/{len(assets_to_refresh)} prices")
                
            except Exception as e:
                log.error(f"Background stock/ETF refresh process failed: {e}")
        
        # Start the background thread
        thread = threading.Thread(target=refresh_all_stocks_bg)
        thread.daemon = True
        thread.start()
        log.info("Started background refresh of stock/ETF prices")
        return
