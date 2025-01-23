import logging
import operator
import sqlite3
from collections.abc import Callable, Iterable, Sequence
from contextlib import suppress
from functools import wraps
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

from rotkehlchen.assets.asset import Asset, AssetWithOracles, EvmToken, FiatAsset, UnderlyingToken
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
    A_POLYGON_POS_MATIC,
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

    This function is neither in inquirer.py or chain/ethereum/defi.py
    due to recursive import problems
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


def handle_recursion_error(return_price_only: bool = False, return_dict: bool = False) -> Callable:
    """
    In the app we saw that having a wrongly configured token which had itself
    as underlying token created a RecursionError. That recursion error was
    tracked in the logs as an error with no traceback and sometimes an OperationalError
    type from sqlite. The recursion error was not only seen here but also in the past
    so we've decided to catch both of them here.

    This decorator is used with methods that return either a single price, a tuple containing
    a price and oracle, or a dict that maps assets to either prices or price and oracle tuples.
    When there is an error, to keep the decorator compatible with the expected returned type,
    if `return_dict` is True we simply return an empty dict, otherwise if `return_price_only`
    is True we return only `Price(ZERO)` and if it's False we return a price and oracle tuple.
    """
    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore
            try:
                result = func(*args, **kwargs)
            except (RecursionError, sqlite3.OperationalError) as e:
                to_asset = kwargs.get('to_asset')
                if return_dict is True:
                    from_assets = kwargs.get('from_assets') or kwargs.get('assets')
                    log.error(
                        f'Failed to query prices {from_assets=} {to_asset=} '
                        f'due to a recursion error: {e}.',
                    )
                    return {}

                from_asset = kwargs.get('from_asset') or kwargs.get('asset')
                log.error(
                    f'Failed to query price {from_asset=} {to_asset=} due to a recursion error: '
                    f'{e}. Using zero as price.',
                )
                if return_price_only:
                    return Price(ZERO)

                return Price(ZERO), CurrentPriceOracle.BLOCKCHAIN
            return result
        return wrapper  # type: ignore
    return decorator


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

    def __new__(
            cls,
            data_dir: Path | None = None,
            cryptocompare: Optional['Cryptocompare'] = None,
            coingecko: Optional['Coingecko'] = None,
            defillama: Optional['Defillama'] = None,
            alchemy: Optional['Alchemy'] = None,
            manualcurrent: Optional['ManualCurrentOracle'] = None,
            msg_aggregator: Optional['MessagesAggregator'] = None,
    ) -> 'Inquirer':
        if Inquirer.__instance is not None:
            return Inquirer.__instance

        error_msg = 'arguments should be given at the first instantiation'
        assert data_dir, error_msg
        assert cryptocompare, error_msg
        assert coingecko, error_msg
        assert defillama, error_msg
        assert alchemy, error_msg
        assert manualcurrent, error_msg
        assert msg_aggregator, error_msg

        Inquirer.__instance = object.__new__(cls)

        Inquirer.__instance._data_directory = data_dir
        Inquirer._cryptocompare = cryptocompare
        Inquirer._coingecko = coingecko
        Inquirer._defillama = defillama
        Inquirer._alchemy = alchemy
        Inquirer._manualcurrent = manualcurrent
        Inquirer._cached_current_price = LRUCacheWithRemove(maxsize=1024)
        Inquirer._evm_managers = {}
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
    def get_cached_current_price_entry(
            cache_key: tuple[Asset, Asset],
    ) -> CachedPriceEntry | None:
        cache = Inquirer._cached_current_price.get(cache_key)
        if cache is None or ts_now() - cache.time > CURRENT_PRICE_CACHE_SECS:
            return None

        return cache

    @staticmethod
    def remove_cache_prices_for_asset(assets_to_invalidate: set[Asset]) -> None:
        """Deletes all prices cache that contains any asset in the possible pairs."""
        for asset_pair in list(Inquirer._cached_current_price.cache):  # create a list to avoid mutating the map while iterating it  # noqa: E501
            if asset_pair[0] in assets_to_invalidate or asset_pair[1] in assets_to_invalidate:
                Inquirer._cached_current_price.remove(asset_pair)

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
        """Save cached price for the key provided and all the assets in the same collection"""
        related_assets = GlobalDBHandler.get_assets_in_same_collection(cache_key[0].identifier)
        for related_asset in related_assets:
            Inquirer._cached_current_price.add((related_asset, cache_key[1]), cached_price)

    @staticmethod
    def _try_oracle_price_query(
            oracle: CurrentPriceOracle,
            oracle_instance: CurrentPriceOracleInstance,
            from_assets: list[AssetWithOracles],
            to_asset: AssetWithOracles,
    ) -> tuple[dict[AssetWithOracles, Price], list[AssetWithOracles]]:
        """Tries to query the current prices of the from_assets
        in to_asset valuation, using the provided oracle instance.
        Returns a tuple containing the following:
        1. dict mapping assets to prices found.
        2. list of assets for which no price was found.

        May raise:
        - RecursionError if `coming_from_latest_price` is True. Used in the ManualCurrentOracle
        """
        pol_token, pos_matic_token = None, None
        if A_POLYGON_POS_MATIC in from_assets and ts_now() > POLYGON_POS_POL_HARDFORK:  # after hardfork, we use different oracles  # noqa: E501
            from_assets.remove(pos_matic_token := A_POLYGON_POS_MATIC.resolve_to_asset_with_oracles())  # noqa: E501
            from_assets.append(pol_token := Asset('eip155:1/erc20:0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6').resolve_to_asset_with_oracles())  # POL token  # noqa: E501

        try:
            prices = oracle_instance.query_multiple_current_price(
                from_assets=from_assets,
                to_asset=to_asset,
            )
        except (DefiPoolError, PriceQueryUnsupportedAsset, RemoteError) as e:
            log.warning(
                f'Current price oracle {oracle_instance} failed to request {to_asset!s} '
                f'price for {from_assets!s} due to: {e!s}.',
            )
            return {}, from_assets

        failed_assets: list[AssetWithOracles] = []
        for from_asset in from_assets:
            if (price := prices.get(from_asset, ZERO_PRICE)) != ZERO_PRICE:
                Inquirer.set_cached_price(
                    cache_key=(from_asset, to_asset),
                    cached_price=CachedPriceEntry(
                        price=price,
                        time=ts_now(),
                        oracle=oracle,
                    ),
                )
            else:  # Either from_asset was recorded with ZERO_PRICE or it is not present in prices
                prices.pop(from_asset, None)
                failed_assets.append(from_asset if pos_matic_token is None else pos_matic_token)

        if pol_token is not None and (pol_price := prices.get(pol_token)) is not None:
            prices[pos_matic_token] = pol_price  # type: ignore[index]  # pos_matic_token will not be None if pol_token is not None
            del prices[pol_token]

        return prices, failed_assets

    @staticmethod
    def _query_oracle_instances(
            from_assets: list[Asset],
            to_asset: Asset,
            skip_onchain: bool = False,
    ) -> dict[Asset, tuple[Price, CurrentPriceOracle]]:
        """Query oracle instances.
        Returns a dict mapping assets to a tuple of the price found and the oracle used.
        If no oracles are able to find an assets price it will be set to ZERO_PRICE.
        """
        instance = Inquirer()
        assert (
            instance._oracles is not None and
            instance._oracle_instances is not None and
            instance._oracles_not_onchain is not None and
            instance._oracle_instances_not_onchain is not None
        ), (
            'Inquirer should never be called before setting the oracles'
        )

        found_prices: dict[Asset, tuple[Price, CurrentPriceOracle]] = {}
        unknown_prices: list[AssetWithOracles] = []

        for from_asset in from_assets:
            if from_asset.is_asset_with_oracles() is True:
                unknown_prices.append(from_asset.resolve_to_asset_with_oracles())
            else:
                found_prices[from_asset] = ZERO_PRICE, CurrentPriceOracle.BLOCKCHAIN

        if len(unknown_prices) == 0:
            return found_prices

        to_asset = to_asset.resolve_to_asset_with_oracles()
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

            prices, unknown_prices = Inquirer._try_oracle_price_query(
                oracle=oracle,
                oracle_instance=oracle_instance,
                from_assets=unknown_prices,
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

            if len(unknown_prices) == 0:
                break

        # Set any assets that are still unknown to zero price
        found_prices.update(dict.fromkeys(unknown_prices, (ZERO_PRICE, CurrentPriceOracle.BLOCKCHAIN)))  # noqa: E501

        return found_prices

    @staticmethod
    def _find_prices(
            from_assets: list[Asset],
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, tuple[Price, CurrentPriceOracle]]:
        """Returns a dict mapping from_assets to tuples containing the following:
        1. The current price of the 'from_asset' in 'to_asset' valuation.
        2. Oracle that was used to get the price.

        NB: prices for special symbols in any currency but USD are not supported.

        If all options for finding a price are unsuccessful the price will be set to ZERO_PRICE,
        and any errors will be logged in the logs.

        `coming_from_latest_price` is used by manual latest price oracle to handle price loops.
        """
        found_prices: dict[Asset, tuple[Price, CurrentPriceOracle]] = {}
        collection_assets: dict[Asset, AssetWithOracles] = {}
        unpriced_assets: list[Asset] = []
        for from_asset in from_assets:
            if from_asset == to_asset:
                found_prices[from_asset] = Price(ONE), CurrentPriceOracle.MANUALCURRENT
                continue

            if (collection_main_asset_id := GlobalDBHandler.get_collection_main_asset(from_asset.identifier)) is not None:  # noqa: E501
                unpriced_assets.append(collection_main_asset := Asset(collection_main_asset_id).resolve_to_asset_with_oracles())  # noqa: E501
                collection_assets[from_asset] = collection_main_asset
            else:
                unpriced_assets.append(from_asset)

        if to_asset == A_USD:
            found_prices.update(Inquirer.find_usd_prices_and_oracles(
                assets=unpriced_assets,
                ignore_cache=ignore_cache,
            ))
            return found_prices

        assets_not_in_cache = []
        if ignore_cache is False:
            for from_asset in unpriced_assets:
                if (cache := Inquirer.get_cached_current_price_entry(cache_key=(from_asset, to_asset))) is not None:  # noqa: E501
                    found_prices[from_asset] = cache.price, cache.oracle
                else:
                    assets_not_in_cache.append(from_asset)

        # check manual prices
        prices, assets_without_manual_price = Inquirer._try_oracle_price_query(
            oracle=CurrentPriceOracle.MANUALCURRENT,
            oracle_instance=Inquirer._manualcurrent,
            from_assets=assets_not_in_cache,  # type: ignore[arg-type]  # Manual current oracle can handle Asset rather than AssetWithOracles
            to_asset=to_asset,  # type: ignore[arg-type]  # Manual current oracle can handle Asset rather than AssetWithOracles
        )
        for from_asset, price in prices.items():
            found_prices[from_asset] = price, CurrentPriceOracle.MANUALCURRENT

        if to_asset.is_fiat():
            non_fiat_assets: list[Asset] = []
            for from_asset in assets_without_manual_price:
                if from_asset.is_fiat():
                    with suppress(RemoteError):
                        price, oracle = Inquirer._query_fiat_pair(
                            base=from_asset.resolve_to_fiat_asset(),
                            quote=to_asset.resolve_to_fiat_asset(),
                        )
                        found_prices[from_asset] = price, oracle
                        continue

                non_fiat_assets.append(from_asset)
        else:
            non_fiat_assets = assets_without_manual_price  # type: ignore[assignment]  # assets_without_manual_price from manual oracle is actually list[Asset]

        found_prices.update(Inquirer._query_oracle_instances(
            from_assets=non_fiat_assets,
            to_asset=to_asset,
            skip_onchain=skip_onchain,
        ))

        # Make sure we're returning the assets that were originally
        # requested rather than just a collection's main asset.
        for asset, main_asset in collection_assets.items():
            found_prices[asset] = found_prices[main_asset]
            if main_asset not in from_assets:
                del found_prices[main_asset]

        return found_prices

    @staticmethod
    @handle_recursion_error(return_price_only=True)
    def find_price(
            from_asset: Asset,
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> Price:
        """Wrapper around find_price_and_oracle to ignore
        the oracle queried when getting a single price.
        """
        price, _ = Inquirer.find_price_and_oracle(
            from_asset=from_asset,
            to_asset=to_asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        )
        return price

    @staticmethod
    @handle_recursion_error()
    def find_price_and_oracle(
            from_asset: Asset,
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> tuple[Price, CurrentPriceOracle]:
        """Wrapper around find_prices_and_oracles to include
        the oracle queried when getting a single price.
        """
        return Inquirer.find_prices_and_oracles(
            from_assets=[from_asset],
            to_asset=to_asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        ).get(from_asset, (ZERO_PRICE, CurrentPriceOracle.BLOCKCHAIN))

    @staticmethod
    @handle_recursion_error(return_dict=True)
    def find_prices(
            from_assets: list[Asset],
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, Price]:
        """Wrapper around _find_prices to ignore the oracle queried when getting prices."""
        return {
            asset: price_and_oracle[0]
            for asset, price_and_oracle in Inquirer._find_prices(
                from_assets=from_assets,
                to_asset=to_asset,
                ignore_cache=ignore_cache,
                skip_onchain=skip_onchain,
            ).items()
        }

    @staticmethod
    @handle_recursion_error(return_dict=True)
    def find_prices_and_oracles(
            from_assets: list[Asset],
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, tuple[Price, CurrentPriceOracle]]:
        """Wrapper around _find_prices to include the oracle queried when getting prices."""
        return Inquirer._find_prices(
            from_assets=from_assets,
            to_asset=to_asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        )

    @staticmethod
    @handle_recursion_error(return_price_only=True)
    def find_usd_price(
            asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> Price:
        """Wrapper around find_usd_price_and_oracle to ignore
        the oracle queried when getting a single usd price.
        """
        price, _ = Inquirer.find_usd_price_and_oracle(
            asset=asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        )
        return price

    @staticmethod
    @handle_recursion_error()
    def find_usd_price_and_oracle(
            asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> tuple[Price, CurrentPriceOracle]:
        """Wrapper around find_usd_prices_and_oracles to include the
        oracle queried when getting a single usd price.
        """
        return Inquirer.find_usd_prices_and_oracles(
            assets=[asset],
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        ).get(asset, (ZERO_PRICE, CurrentPriceOracle.FIAT))

    @staticmethod
    @handle_recursion_error(return_dict=True)
    def find_usd_prices(
            assets: list[Asset],
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, Price]:
        """Wrapper around _find_usd_prices to ignore the oracle queried when getting prices."""
        return {
            asset: price_and_oracle[0]
            for asset, price_and_oracle in Inquirer._find_usd_prices(
                assets=assets,
                ignore_cache=ignore_cache,
                skip_onchain=skip_onchain,
            ).items()
        }

    @staticmethod
    @handle_recursion_error(return_dict=True)
    def find_usd_prices_and_oracles(
            assets: list[Asset],
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, tuple[Price, CurrentPriceOracle]]:
        """Wrapper around _find_usd_prices to include the
        oracles queried when getting usd prices.
        """
        return Inquirer._find_usd_prices(
            assets=assets,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
        )

    @staticmethod
    def _find_usd_prices(
            assets: list[Asset],
            ignore_cache: bool = False,
            skip_onchain: bool = False,
    ) -> dict[Asset, tuple[Price, CurrentPriceOracle]]:
        """Returns a dict mapping assets to a tuple of the price found and the oracle used.
        If all options for finding a price are unsuccessful the price will be set to ZERO_PRICE,
        and any errors will be logged in the logs.
        """
        found_prices: dict[Asset, tuple[Price, CurrentPriceOracle]] = {}

        # Retrieve prices from the cache, and set
        assets_without_price: list[Asset] = []
        for asset in assets:
            if asset == A_USD:
                found_prices[asset] = Price(ONE), CurrentPriceOracle.FIAT
                continue
            elif asset == A_ETH2:
                asset = A_ETH  # noqa: PLW2901  # we do want to overwrite the loop variable

            if ignore_cache is False:
                cache = Inquirer.get_cached_current_price_entry(cache_key=(asset, A_USD))
                if cache is not None:
                    found_prices[asset] = cache.price, cache.oracle
                    continue

            try:
                resolved_asset = asset.resolve()
            except UnknownAsset:
                log.error(f'Tried to ask for {asset.identifier} price but asset is missing from the DB')  # noqa: E501
                found_prices[asset] = ZERO_PRICE, CurrentPriceOracle.FIAT
                continue

            if isinstance(resolved_asset, FiatAsset):
                with suppress(RemoteError):
                    found_prices[resolved_asset] = Inquirer._query_fiat_pair(
                        base=resolved_asset,
                        quote=Inquirer.usd,
                    )
                    continue

            assets_without_price.append(resolved_asset)

        if len(assets_without_price) == 0:
            return found_prices  # All prices have been found in the loop above

        # continue, assets aren't fiat, check manual prices
        prices, assets_without_price = Inquirer._try_oracle_price_query(  # type: ignore[assignment]  # Manual current oracle uses Asset type
            oracle=CurrentPriceOracle.MANUALCURRENT,
            oracle_instance=Inquirer._manualcurrent,
            from_assets=assets_without_price,  # type: ignore[arg-type]  # Manual current oracle works with Asset type
            to_asset=A_USD.resolve_to_asset_with_oracles(),
        )
        for asset, price in prices.items():
            found_prices[asset] = price, CurrentPriceOracle.MANUALCURRENT

        for asset in assets_without_price:
            # Try and check if it is an ethereum token with specified protocol or underlying tokens
            is_known_protocol = False
            if isinstance(asset, EvmToken):
                if asset.protocol is not None:
                    is_known_protocol = asset.protocol in ProtocolsWithPriceLogic
                underlying_tokens = asset.underlying_tokens

                # Check if it is a special token
                if asset.identifier in Inquirer.special_tokens:
                    ethereum = Inquirer.get_evm_manager(chain_id=ChainID.ETHEREUM)
                    underlying_asset_price, oracle = get_underlying_asset_price(asset)
                    usd_price = handle_defi_price_query(
                        ethereum=ethereum.node_inquirer,  # type:ignore  # ethereum is an EthereumManager so the inquirer is of the expected type
                        token=asset,
                        underlying_asset_price=underlying_asset_price,
                    )
                    price = ZERO_PRICE if usd_price is None else Price(usd_price)

                    Inquirer.set_cached_price(
                        cache_key=(asset, A_USD),
                        cached_price=CachedPriceEntry(
                            price=price,
                            time=ts_now(),
                            oracle=CurrentPriceOracle.BLOCKCHAIN,
                        ),
                    )
                    found_prices[asset] = price, oracle
                    continue

                if is_known_protocol is True or underlying_tokens is not None:
                    if (
                        underlying_tokens is not None and
                        asset.evm_address in (x.address for x in underlying_tokens)
                    ):
                        Inquirer._msg_aggregator.add_error(
                            f'Token {asset} has itself as underlying token. Please edit the '
                            'asset to fix it. Price queries will not work until this is done.',
                        )
                    else:
                        result, oracle = get_underlying_asset_price(asset)
                        if result is not None:
                            Inquirer.set_cached_price(
                                cache_key=(asset, A_USD),
                                cached_price=CachedPriceEntry(
                                    price=(usd_price := Price(result)),
                                    time=ts_now(),
                                    oracle=oracle,
                                ),
                            )
                            found_prices[asset] = usd_price, oracle
                            continue
                    # else known protocol on-chain query failed. Continue to external oracles

            if asset == A_BSQ:
                # BSQ is defined as 100 satohis but can be traded. Before we were using an api
                # to query the BSQ market but it isn't available anymore so we assume BTC_PER_BSQ
                # to obtain a price based on BTC price.
                btc_price = Inquirer.find_usd_price(A_BTC)
                found_prices[asset] = Price(BTC_PER_BSQ * btc_price), CurrentPriceOracle.BLOCKCHAIN
                continue

            if asset == A_KFEE:
                # KFEE is a kraken special asset where 1000 KFEE = 10 USD
                found_prices[asset] = Price(FVal(0.01)), CurrentPriceOracle.FIAT
                continue

        # Query prices from the oracles for any assets whose price has not already been found.
        if len(assets_to_query := [
            asset for asset in assets_without_price
            if asset not in found_prices
        ]) != 0:
            found_prices.update(Inquirer._query_oracle_instances(
                from_assets=assets_to_query,
                to_asset=A_USD,
                skip_onchain=skip_onchain,
            ))

        return found_prices

    def find_lp_price_from_uniswaplike_pool(
            self,
            token: EvmToken,
    ) -> Price | None:
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
            try:
                price, _ = Inquirer()._query_fiat_pair(
                    base=instance.usd,
                    quote=currency,
                )
                rates[currency] = price
            except RemoteError:
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
    def _query_fiat_pair(
            base: FiatAsset,
            quote: FiatAsset,
    ) -> tuple[Price, CurrentPriceOracle]:
        """Queries the current price between two fiat assets

        If a current price is not found but a cached price within 30 days is found
        then that one is used.

        May raise RemoteError if a price can not be found
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
        raise RemoteError(
            f'Could not find a current {base.identifier} price for {quote.identifier}',
        )

    @staticmethod
    def clear() -> None:
        """
        ensure that we don't have oracles that depend on the logged
        in user. Calling `set_oracles_order` if we want to use the Inquirer
        again is required.
        """
        inquirer = Inquirer()
        inquirer._uniswapv2 = None
        inquirer._uniswapv3 = None
        del inquirer._oracle_instances
        del inquirer._oracles
        del inquirer._oracle_instances_not_onchain
        del inquirer._oracles_not_onchain
