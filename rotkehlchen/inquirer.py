from __future__ import unicode_literals  # isort:skip

import logging
import operator
from enum import auto
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

from rotkehlchen.assets.asset import Asset, EvmToken, FiatAsset
from rotkehlchen.chain.ethereum.defi.price import handle_defi_price_query
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import CURRENCYCONVERTER_API_KEY, ONE, ZERO
from rotkehlchen.constants.assets import (
    A_3CRV,
    A_ALINK_V1,
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
    A_FARM_CRVRENWBTC,
    A_FARM_DAI,
    A_FARM_RENBTC,
    A_FARM_TUSD,
    A_FARM_USDC,
    A_FARM_USDT,
    A_FARM_WBTC,
    A_FARM_WETH,
    A_GUSD,
    A_KFEE,
    A_TUSD,
    A_USD,
    A_USDC,
    A_USDT,
    A_WETH,
    A_YFI,
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
from rotkehlchen.constants.ethereum import CURVE_POOL_ABI, YEARN_VAULT_V2_ABI
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.constants.timing import DAY_IN_SECONDS, MONTH_IN_SECONDS
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.defi import DefiPoolError
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.price import PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.bisq_market import get_bisq_market_price
from rotkehlchen.externalapis.xratescom import (
    get_current_xratescom_exchange_rates,
    get_historical_xratescom_exchange_rates,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    CURVE_POOL_PROTOCOL,
    UNISWAP_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    ChainID,
    GeneralCacheType,
    KnownProtocolsAssets,
    OracleSource,
    Price,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_daystart_timestamp, ts_now
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.oracles.saddle import SaddleOracle
    from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.externalapis.defillama import Defillama
    from rotkehlchen.globaldb.manual_price_oracles import ManualCurrentOracle


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CURRENT_PRICE_CACHE_SECS = 300  # 5 mins
DEFAULT_RATE_LIMIT_WAITING_TIME = 60  # seconds
BTC_PER_BSQ = FVal('0.00000100')

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
    'UniswapV3Oracle',
    'UniswapV2Oracle',
    'SaddleOracle',
    'ManualCurrentOracle',
]


def _check_curve_contract_call(decoded: Tuple[Any, ...]) -> bool:
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


class CurrentPriceOracle(OracleSource):
    """Supported oracles for querying current prices"""
    COINGECKO = auto()
    CRYPTOCOMPARE = auto()
    UNISWAPV2 = auto()
    UNISWAPV3 = auto()
    SADDLE = auto()
    MANUALCURRENT = auto()
    BLOCKCHAIN = auto()
    FIAT = auto()
    DEFILLAMA = auto()


DEFAULT_CURRENT_PRICE_ORACLES_ORDER = [
    CurrentPriceOracle.MANUALCURRENT,
    CurrentPriceOracle.COINGECKO,
    CurrentPriceOracle.DEFILLAMA,
    CurrentPriceOracle.CRYPTOCOMPARE,
    CurrentPriceOracle.UNISWAPV2,
    CurrentPriceOracle.UNISWAPV3,
    CurrentPriceOracle.SADDLE,
]


def get_underlying_asset_price(token: EvmToken) -> Tuple[Optional[Price], CurrentPriceOracle]:  # noqa: E501
    """Gets the underlying asset price for the given ethereum token

    TODO: This should be eventually pulled from the assets DB. All of these
    need to be updated, to contain proper protocol, and underlying assets.

    This function is neither in inquirer.py or chain/ethereum/defi.py
    due to recursive import problems
    """
    price, oracle = None, CurrentPriceOracle.BLOCKCHAIN
    if token.protocol == UNISWAP_PROTOCOL:
        price = Inquirer().find_uniswap_v2_lp_price(token)
        oracle = CurrentPriceOracle.UNISWAPV2
    elif token.protocol == CURVE_POOL_PROTOCOL:
        price = Inquirer().find_curve_pool_price(token)
        oracle = CurrentPriceOracle.BLOCKCHAIN
    elif token.protocol == YEARN_VAULTS_V2_PROTOCOL:
        price = Inquirer().find_yearn_price(token)
        oracle = CurrentPriceOracle.BLOCKCHAIN

    if token == A_YV1_ALINK:
        price, oracle = Inquirer().find_usd_price_and_oracle(A_ALINK_V1)
    elif token == A_YV1_GUSD:
        price, oracle = Inquirer().find_usd_price_and_oracle(A_GUSD)
    elif token in (A_YV1_DAI, A_FARM_DAI):
        price, oracle = Inquirer().find_usd_price_and_oracle(A_DAI)
    elif token in (A_FARM_WETH, A_YV1_WETH):
        price, oracle = Inquirer().find_usd_price_and_oracle(A_ETH)
    elif token == A_YV1_YFI:
        price, oracle = Inquirer().find_usd_price_and_oracle(A_YFI)
    elif token in (A_FARM_USDT, A_YV1_USDT):
        price, oracle = Inquirer().find_usd_price_and_oracle(A_USDT)
    elif token in (A_FARM_USDC, A_YV1_USDC):
        price, oracle = Inquirer().find_usd_price_and_oracle(A_USDC)
    elif token in (A_FARM_TUSD, A_YV1_TUSD):
        price, oracle = Inquirer().find_usd_price_and_oracle(A_TUSD)
    elif token in ASSETS_UNDERLYING_BTC:
        price, oracle = Inquirer().find_usd_price_and_oracle(A_BTC)

    # At this point we have to return the price if it's not None. If we don't do this and got
    # a price for a token that has underlying assets, the code will enter the if statement after
    # this block and the value for price will change becoming incorrect.
    if price is not None:
        return price, oracle

    custom_token = GlobalDBHandler().get_evm_token(
        address=token.evm_address,
        chain=ChainID.ETHEREUM,
    )
    if custom_token and custom_token.underlying_tokens is not None:
        usd_price = ZERO
        for underlying_token in custom_token.underlying_tokens:
            token = EvmToken(underlying_token.get_identifier(parent_chain=custom_token.chain))
            underlying_asset_price, oracle = Inquirer().find_usd_price_and_oracle(token)
            usd_price += underlying_asset_price * underlying_token.weight

        if usd_price != Price(ZERO):
            price = Price(usd_price)

    return price, oracle


def _query_currency_converterapi(base: FiatAsset, quote: FiatAsset) -> Optional[Price]:
    log.debug(
        'Query free.currencyconverterapi.com fiat pair',
        base_currency=base.identifier,
        quote_currency=quote.identifier,
    )
    pair = f'{base.identifier}_{quote.identifier}'
    querystr = (
        f'https://free.currconv.com/api/v7/convert?'
        f'q={pair}&compact=ultra&apiKey={CURRENCYCONVERTER_API_KEY}'
    )
    try:
        resp = request_get_dict(querystr)
        return Price(FVal(resp[pair]))
    except (ValueError, RemoteError, KeyError, UnableToDecryptRemoteData):
        log.error(
            'Querying free.currencyconverterapi.com fiat pair failed',
            base_currency=base.identifier,
            quote_currency=quote.identifier,
        )
        return None


class CachedPriceEntry(NamedTuple):
    price: Price
    time: Timestamp
    oracle: CurrentPriceOracle


class Inquirer():
    __instance: Optional['Inquirer'] = None
    _cached_forex_data: Dict
    _cached_current_price: Dict[Tuple[Asset, Asset], CachedPriceEntry]
    _data_directory: Path
    _cryptocompare: 'Cryptocompare'
    _coingecko: 'Coingecko'
    _defillama: 'Defillama'
    _manualcurrent: 'ManualCurrentOracle'
    _uniswapv2: Optional['UniswapV2Oracle'] = None
    _uniswapv3: Optional['UniswapV3Oracle'] = None
    _saddle: Optional['SaddleOracle'] = None
    _ethereum: Optional['EthereumManager'] = None
    _oracles: Optional[List[CurrentPriceOracle]] = None
    _oracle_instances: Optional[List[CurrentPriceOracleInstance]] = None
    _oracles_not_onchain: Optional[List[CurrentPriceOracle]] = None
    _oracle_instances_not_onchain: Optional[List[CurrentPriceOracleInstance]] = None
    _msg_aggregator: 'MessagesAggregator'
    # save only the identifier of the special tokens since we only check if assets are in this set
    special_tokens: Set[str]
    weth: EvmToken
    usd: FiatAsset

    def __new__(
            cls,
            data_dir: Path = None,
            cryptocompare: 'Cryptocompare' = None,
            coingecko: 'Coingecko' = None,
            defillama: 'Defillama' = None,
            manualcurrent: 'ManualCurrentOracle' = None,
            msg_aggregator: 'MessagesAggregator' = None,
    ) -> 'Inquirer':
        if Inquirer.__instance is not None:
            return Inquirer.__instance

        error_msg = 'arguments should be given at the first instantiation'
        assert data_dir, error_msg
        assert cryptocompare, error_msg
        assert coingecko, error_msg
        assert defillama, error_msg
        assert manualcurrent, error_msg
        assert msg_aggregator, error_msg

        Inquirer.__instance = object.__new__(cls)

        Inquirer.__instance._data_directory = data_dir
        Inquirer._cryptocompare = cryptocompare
        Inquirer._coingecko = coingecko
        Inquirer._defillama = defillama
        Inquirer._manualcurrent = manualcurrent
        Inquirer._cached_current_price = {}
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
        }
        try:
            Inquirer.usd = A_USD.resolve_to_fiat_asset()
            Inquirer.weth = A_WETH.resolve_to_evm_token()
        except (UnknownAsset, WrongAssetType) as e:
            message = f'One of the base assets was deleted/modified from the DB: {str(e)}'
            log.critical(message)
            raise RuntimeError(message + '. Add it back manually or contact support') from e

        return Inquirer.__instance

    @staticmethod
    def inject_ethereum(ethereum: 'EthereumManager') -> None:
        Inquirer()._ethereum = ethereum

    @staticmethod
    def add_defi_oracles(
        uniswap_v2: Optional['UniswapV2Oracle'],
        uniswap_v3: Optional['UniswapV3Oracle'],
        saddle: Optional['SaddleOracle'],
    ) -> None:
        Inquirer()._uniswapv2 = uniswap_v2
        Inquirer()._uniswapv3 = uniswap_v3
        Inquirer()._saddle = saddle

    @staticmethod
    def get_cached_current_price_entry(cache_key: Tuple[Asset, Asset]) -> Optional[CachedPriceEntry]:  # noqa: E501
        cache = Inquirer()._cached_current_price.get(cache_key, None)
        if cache is None or ts_now() - cache.time > CURRENT_PRICE_CACHE_SECS:
            return None

        return cache

    @staticmethod
    def remove_cache_prices_for_asset(pairs_to_invalidate: List[Tuple[Asset, Asset]]) -> None:
        """Deletes all prices cache that contains any asset in the possible pairs."""
        assets_to_invalidate = set()
        for asset_a, asset_b in pairs_to_invalidate:
            assets_to_invalidate.add(asset_a)
            assets_to_invalidate.add(asset_b)

        for asset_pair in list(Inquirer()._cached_current_price):
            if asset_pair[0] in assets_to_invalidate or asset_pair[1] in assets_to_invalidate:
                Inquirer()._cached_current_price.pop(asset_pair, None)

    @staticmethod
    def remove_cached_current_price_entry(cache_key: Tuple[Asset, Asset]) -> None:
        Inquirer()._cached_current_price.pop(cache_key, None)

    @staticmethod
    def set_oracles_order(oracles: List[CurrentPriceOracle]) -> None:
        assert len(oracles) != 0 and len(oracles) == len(set(oracles)), (
            'Oracles can\'t be empty or have repeated items'
        )
        instance = Inquirer()
        instance._oracles = oracles
        instance._oracle_instances = [getattr(instance, f'_{str(oracle)}') for oracle in oracles]
        instance._oracles_not_onchain = []
        instance._oracle_instances_not_onchain = []
        for oracle, oracle_instance in zip(instance._oracles, instance._oracle_instances):
            if oracle not in (CurrentPriceOracle.UNISWAPV2, CurrentPriceOracle.UNISWAPV3, CurrentPriceOracle.SADDLE):  # noqa: E501
                instance._oracles_not_onchain.append(oracle)
                instance._oracle_instances_not_onchain.append(oracle_instance)

    @staticmethod
    def _query_oracle_instances(
            from_asset: Asset,
            to_asset: Asset,
            coming_from_latest_price: bool,
            skip_onchain: bool = False,
    ) -> Tuple[Price, CurrentPriceOracle]:
        """
        Query oracle instances.
        `coming_from_latest_price` is used by manual latest price oracle to handle price loops.
        """
        instance = Inquirer()
        cache_key = (from_asset, to_asset)
        assert (
            isinstance(instance._oracles, list) and
            isinstance(instance._oracle_instances, list) and
            isinstance(instance._oracles_not_onchain, list) and
            isinstance(instance._oracle_instances_not_onchain, list)
        ), (
            'Inquirer should never be called before the setting the oracles'
        )
        if from_asset.is_asset_with_oracles() is True:
            from_asset = from_asset.resolve_to_asset_with_oracles()
            to_asset = to_asset.resolve_to_asset_with_oracles()
            if skip_onchain:
                oracles = instance._oracles_not_onchain
                oracle_instances = instance._oracle_instances_not_onchain
            else:
                oracles = instance._oracles
                oracle_instances = instance._oracle_instances
        else:
            oracles = [CurrentPriceOracle.MANUALCURRENT]
            oracle_instances = [instance._manualcurrent]

        price = Price(ZERO)
        oracle_queried = CurrentPriceOracle.BLOCKCHAIN
        for oracle, oracle_instance in zip(oracles, oracle_instances):
            if (
                isinstance(oracle_instance, CurrentPriceOracleInterface) and
                oracle_instance.rate_limited_in_last(DEFAULT_RATE_LIMIT_WAITING_TIME) is True
            ):
                continue

            try:
                price = oracle_instance.query_current_price(
                    from_asset=from_asset,  # type: ignore  # type is guaranteed by the if above
                    to_asset=to_asset,  # type: ignore  # type is guaranteed by the if above
                )
            except (DefiPoolError, PriceQueryUnsupportedAsset, RemoteError) as e:
                log.warning(
                    f'Current price oracle {oracle} failed to request {to_asset.identifier} '
                    f'price for {from_asset.identifier} due to: {str(e)}.',
                )
                continue
            except RecursionError:
                # We have to catch recursion error only at the top level since otherwise we get to
                # recursion level MAX - 1, and after calling some other function may run into it again.  # noqa: E501
                if coming_from_latest_price is True:
                    raise

                # else
                # Infinite loop can happen if user creates a loop of manual current prices
                # (e.g. said that 1 BTC costs 2 ETH and 1 ETH costs 5 BTC).
                instance._msg_aggregator.add_warning(
                    f'Was not able to find price from {str(from_asset)} to {str(to_asset)} since your '  # noqa: E501
                    f'manual latest prices form a loop. For now, other oracles will be used.',
                )
                continue

            if price != Price(ZERO):
                oracle_queried = oracle
                log.debug(
                    f'Current price oracle {oracle} got price',
                    from_asset=from_asset,
                    to_asset=to_asset,
                    price=price,
                )
                break

        Inquirer._cached_current_price[cache_key] = CachedPriceEntry(
            price=price,
            time=ts_now(),
            oracle=oracle_queried,
        )
        return price, oracle_queried

    @staticmethod
    def _find_price(
            from_asset: Asset,
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
            coming_from_latest_price: bool = False,
    ) -> Tuple[Price, CurrentPriceOracle]:
        """Returns the current price of 'from_asset' in 'to_asset' valuation.
        NB: prices for special symbols in any currency but USD are not supported.

        Returns Price(ZERO) if all options have been exhausted and errors are logged in the logs.
        `coming_from_latest_price` is used by manual latest price oracle to handle price loops.
        """
        if from_asset == to_asset:
            return Price(ONE), CurrentPriceOracle.MANUALCURRENT

        instance = Inquirer()
        if to_asset == A_USD:
            return instance.find_usd_price_and_oracle(
                asset=from_asset,
                ignore_cache=ignore_cache,
                coming_from_latest_price=coming_from_latest_price,
            )

        if ignore_cache is False:
            cache = instance.get_cached_current_price_entry(cache_key=(from_asset, to_asset))
            if cache is not None:
                return cache.price, cache.oracle

        oracle_price, oracle_queried = instance._query_oracle_instances(
            from_asset=from_asset,
            to_asset=to_asset,
            skip_onchain=skip_onchain,
            coming_from_latest_price=coming_from_latest_price,
        )
        return oracle_price, oracle_queried

    @staticmethod
    def find_price(
            from_asset: Asset,
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
            coming_from_latest_price: bool = False,
    ) -> Price:
        """Wrapper around _find_price to ignore oracle queried when getting price"""
        price, _ = Inquirer()._find_price(
            from_asset=from_asset,
            to_asset=to_asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
            coming_from_latest_price=coming_from_latest_price,
        )
        return price

    @staticmethod
    def find_price_and_oracle(
            from_asset: Asset,
            to_asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
            coming_from_latest_price: bool = False,
    ) -> Tuple[Price, CurrentPriceOracle]:
        """Wrapper around _find_price to include oracle queried when getting price"""
        return Inquirer()._find_price(
            from_asset=from_asset,
            to_asset=to_asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
            coming_from_latest_price=coming_from_latest_price,
        )

    @staticmethod
    def find_usd_price(
            asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
            coming_from_latest_price: bool = False,
    ) -> Price:
        """Wrapper around _find_usd_price to ignore oracle queried when getting usd price"""
        price, _ = Inquirer()._find_usd_price(
            asset=asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
            coming_from_latest_price=coming_from_latest_price,
        )
        return price

    @staticmethod
    def find_usd_price_and_oracle(
            asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
            coming_from_latest_price: bool = False,
    ) -> Tuple[Price, CurrentPriceOracle]:
        """Wrapper around _find_usd_price to include oracle queried when getting usd price"""
        return Inquirer()._find_usd_price(
            asset=asset,
            ignore_cache=ignore_cache,
            skip_onchain=skip_onchain,
            coming_from_latest_price=coming_from_latest_price,
        )

    @staticmethod
    def _find_usd_price(
            asset: Asset,
            ignore_cache: bool = False,
            skip_onchain: bool = False,
            coming_from_latest_price: bool = False,
    ) -> Tuple[Price, CurrentPriceOracle]:
        """Returns the current USD price of the asset

        Returns Price(ZERO) if all options have been exhausted and errors are logged in the logs.
        `coming_from_latest_price` is used by manual latest price oracle to handle price loops.
        """
        if asset == A_USD:
            return Price(ONE), CurrentPriceOracle.FIAT

        instance = Inquirer()
        cache_key = (asset, A_USD)
        if ignore_cache is False:
            cache = instance.get_cached_current_price_entry(cache_key=cache_key)
            if cache is not None:
                return cache.price, cache.oracle

        try:
            asset = asset.resolve_to_fiat_asset()
            return instance._query_fiat_pair(base=asset, quote=instance.usd)
        except (UnknownAsset, RemoteError, WrongAssetType):
            pass  # continue, asset is not fiat or a price can be found by one of the oracles (CC for example)  # noqa: E501

        # Try and check if it is an ethereum token with specified protocol or underlying tokens
        is_known_protocol = False
        underlying_tokens = None
        try:
            token = asset.resolve_to_evm_token()
            if token.protocol is not None:
                is_known_protocol = token.protocol in KnownProtocolsAssets
            underlying_tokens = token.underlying_tokens
        except (UnknownAsset, WrongAssetType):
            pass

        # Check if it is a special token
        if asset.identifier in instance.special_tokens:
            ethereum = instance._ethereum
            assert ethereum, 'Inquirer should never be called before the injection of ethereum'
            assert token, 'all assets in special tokens are already ethereum tokens'
            underlying_asset_price, oracle = get_underlying_asset_price(token)
            usd_price = handle_defi_price_query(
                ethereum=ethereum,
                token=token,
                underlying_asset_price=underlying_asset_price,
            )
            if usd_price is None:
                price = Price(ZERO)
            else:
                price = Price(usd_price)

            Inquirer._cached_current_price[cache_key] = CachedPriceEntry(price=price, time=ts_now(), oracle=CurrentPriceOracle.BLOCKCHAIN)  # noqa: E501
            return price, oracle

        if is_known_protocol is True or underlying_tokens is not None:
            assert token is not None
            result, oracle = get_underlying_asset_price(token)
            if result is None:
                usd_price = Price(ZERO)
                if instance._ethereum is not None:
                    instance._ethereum.msg_aggregator.add_warning(
                        f'Could not find price for {token}',
                    )
            else:
                usd_price = Price(result)
            Inquirer._cached_current_price[cache_key] = CachedPriceEntry(
                price=usd_price,
                time=ts_now(),
                oracle=oracle,
            )
            return usd_price, oracle

        # BSQ is a special asset that doesnt have oracle information but its custom API
        if asset == A_BSQ:
            try:
                bsq = A_BSQ.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                log.error('Asked for BSQ price but BSQ is missing or misclassified in the global DB')  # noqa: E501
                return Price(ZERO), oracle

            try:
                price_in_btc = get_bisq_market_price(bsq)
                btc_price, oracle = Inquirer().find_usd_price_and_oracle(A_BTC)
                usd_price = Price(price_in_btc * btc_price)
                Inquirer._cached_current_price[cache_key] = CachedPriceEntry(
                    price=usd_price,
                    time=ts_now(),
                    oracle=oracle,
                )
                return usd_price, oracle
            except (RemoteError, DeserializationError) as e:
                msg = f'Could not find price for BSQ. {str(e)}'
                if instance._ethereum is not None:
                    instance._ethereum.msg_aggregator.add_warning(msg)
                return Price(BTC_PER_BSQ * price_in_btc), CurrentPriceOracle.BLOCKCHAIN

        if asset == A_KFEE:
            # KFEE is a kraken special asset where 1000 KFEE = 10 USD
            return Price(FVal(0.01)), CurrentPriceOracle.FIAT

        return instance._query_oracle_instances(
            from_asset=asset,
            to_asset=A_USD,
            coming_from_latest_price=coming_from_latest_price,
            skip_onchain=skip_onchain,
        )

    def find_uniswap_v2_lp_price(
            self,
            token: EvmToken,
    ) -> Optional[Price]:
        assert self._ethereum is not None, 'Inquirer ethereum manager should have been initialized'  # noqa: E501
        # BAD BAD BAD. TODO: Need to rethinking placement of modules here
        from rotkehlchen.chain.ethereum.modules.uniswap.utils import find_uniswap_v2_lp_price  # isort:skip  # noqa: E501  # pylint: disable=import-outside-toplevel
        return find_uniswap_v2_lp_price(
            ethereum=self._ethereum,
            token=token,
            token_price_func=self.find_usd_price,
            token_price_func_args=[],
            block_identifier='latest',
        )

    def find_curve_pool_price(
            self,
            lp_token: EvmToken,
    ) -> Optional[Price]:
        """
        1. Obtain the pool for this token
        2. Obtain prices for assets in pool
        3. Obtain the virtual price for share and the balances of each
        token in the pool
        4. Calc the price for a share

        Returns the price of 1 LP token from the pool
        """
        assert self._ethereum is not None, 'Inquirer ethereum manager should have been initialized'  # noqa: E501
        # Make sure that the curve cache is queried
        self._ethereum.curve_protocol_cache_is_queried(tx_decoder=None)

        pool_addresses_in_cache = GlobalDBHandler().get_general_cache_values(
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token.evm_address],
        )
        if len(pool_addresses_in_cache) == 0:
            return None
        # pool address is guaranteed to be checksumed due to how we save it
        pool_address = string_to_evm_address(pool_addresses_in_cache[0])
        pool_tokens_addresses = GlobalDBHandler().get_general_cache_values(
            key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, pool_address],
        )
        tokens: List[EvmToken] = []
        # Translate addresses to tokens
        try:
            for token_address_str in pool_tokens_addresses:
                token_address = string_to_evm_address(token_address_str)
                if token_address == '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE':
                    tokens.append(self.weth)
                else:
                    token_identifier = ethaddress_to_identifier(token_address)
                    tokens.append(EvmToken(token_identifier))
        except UnknownAsset:
            return None

        # Get price for each token in the pool
        prices = []
        for token in tokens:
            price = self.find_usd_price(token)
            if price == Price(ZERO):
                log.error(
                    f'Could not calculate price for {lp_token} due to inability to '
                    f'fetch price for {token}.',
                )
                return None
            prices.append(price)

        # Query virtual price of LP share and balances in the pool for each token
        contract = EvmContract(
            address=pool_address,
            abi=CURVE_POOL_ABI,
            deployed_block=0,
        )
        calls = [(pool_address, contract.encode(method_name='get_virtual_price'))]
        calls += [
            (pool_address, contract.encode(method_name='balances', arguments=[i]))
            for i in range(len(tokens))
        ]
        output = self._ethereum.multicall_2(
            require_success=False,
            calls=calls,
        )

        # Check that the output has the correct structure
        if not all([len(call_result) == 2 for call_result in output]):
            log.debug(
                f'Failed to query contract methods while finding curve pool price. '
                f'Not every outcome has length 2. {output}',
            )
            return None
        # Check that all the requests were successful
        if not all([contract_output[0] for contract_output in output]):
            log.debug(f'Failed to query contract methods while finding curve price. {output}')
            return None
        # Deserialize information obtained in the multicall execution
        data = []
        # https://github.com/PyCQA/pylint/issues/4739
        virtual_price_decoded = contract.decode(output[0][1], 'get_virtual_price')  # pylint: disable=unsubscriptable-object  # noqa: E501
        if not _check_curve_contract_call(virtual_price_decoded):
            log.debug(f'Failed to decode get_virtual_price while finding curve price. {output}')
            return None
        data.append(FVal(virtual_price_decoded[0]))  # pylint: disable=unsubscriptable-object
        for i, token in enumerate(tokens):
            amount_decoded = contract.decode(output[i + 1][1], 'balances', arguments=[i])
            if not _check_curve_contract_call(amount_decoded):
                log.debug(f'Failed to decode balances {i} while finding curve price. {output}')
                return None
            # https://github.com/PyCQA/pylint/issues/4739
            amount = amount_decoded[0]  # pylint: disable=unsubscriptable-object
            normalized_amount = token_normalized_value_decimals(amount, token.decimals)
            data.append(normalized_amount)

        # Prices and data should verify this relation for the following operations
        if len(prices) != len(data) - 1:
            log.debug(
                f'Length of prices {len(prices)} does not match len of data {len(data)} '
                f'while querying curve pool price.',
            )
            return None
        # Total number of assets price in the pool
        total_assets_price = sum(map(operator.mul, data[1:], prices))
        if total_assets_price == 0:
            log.error(
                f'Curve pool price returned unexpected data {data} that lead to a zero price.',
            )
            return None

        # Calculate weight of each asset as the proportion of tokens value
        weights = (data[x + 1] * prices[x] / total_assets_price for x in range(len(tokens)))
        assets_price = FVal(sum(map(operator.mul, weights, prices)))
        return (assets_price * FVal(data[0])) / (10 ** lp_token.decimals)

    def find_yearn_price(
        self,
        token: EvmToken,
    ) -> Optional[Price]:
        """
        Query price for a yearn vault v2 token using the pricePerShare method
        and the price of the underlying token.
        """
        assert self._ethereum is not None, 'Inquirer ethereum manager should have been initialized'  # noqa: E501

        globaldb = GlobalDBHandler()
        with globaldb.conn.read_ctx() as cursor:
            maybe_underlying_token = globaldb.fetch_underlying_tokens(cursor, ethaddress_to_identifier(token.evm_address))  # noqa: E501
        if maybe_underlying_token is None or len(maybe_underlying_token) != 1:
            log.error(f'Yearn vault token {token} without an underlying asset')
            return None

        underlying_token = EvmToken(ethaddress_to_identifier(maybe_underlying_token[0].address))
        underlying_token_price = self.find_usd_price(underlying_token)
        # Get the price per share from the yearn contract
        contract = EvmContract(
            address=token.evm_address,
            abi=YEARN_VAULT_V2_ABI,
            deployed_block=0,
        )
        try:
            price_per_share = contract.call(self._ethereum, 'pricePerShare')
            return Price(price_per_share * underlying_token_price / 10 ** token.decimals)
        except (RemoteError, BlockchainQueryError) as e:
            log.error(f'Failed to query pricePerShare method in Yearn v2 Vault. {str(e)}')

        return None

    @staticmethod
    def get_fiat_usd_exchange_rates(currencies: Iterable[FiatAsset]) -> Dict[FiatAsset, Price]:  # noqa: E501
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
                rates[currency] = Price(ZERO)

        return rates

    @staticmethod
    def query_historical_fiat_exchange_rates(
            from_fiat_currency: FiatAsset,
            to_fiat_currency: FiatAsset,
            timestamp: Timestamp,
    ) -> Optional[Price]:
        assert from_fiat_currency.is_fiat(), 'fiat currency should have been provided'
        assert to_fiat_currency.is_fiat(), 'fiat currency should have been provided'

        if from_fiat_currency == to_fiat_currency:
            return Price(ONE)

        # Check cache
        price_cache_entry = GlobalDBHandler().get_historical_price(
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
        for asset, asset_price in prices_map.items():
            GlobalDBHandler().add_historical_prices(entries=[HistoricalPrice(
                from_asset=from_fiat_currency,
                to_asset=asset,
                source=HistoricalPriceOracle.XRATESCOM,
                timestamp=timestamp_to_daystart_timestamp(timestamp),
                price=asset_price,
            )])
            if asset == to_fiat_currency:
                rate = asset_price

        log.debug('Historical fiat exchange rate query succesful', rate=rate)
        return rate

    @staticmethod
    def _query_fiat_pair(
            base: FiatAsset,
            quote: FiatAsset,
    ) -> Tuple[Price, CurrentPriceOracle]:
        """Queries the current price between two fiat assets

        If a current price is not found but a cached price within 30 days is found
        then that one is used.

        May raise RemoteError if a price can not be found
        """
        if base == quote:
            return Price(ONE), CurrentPriceOracle.FIAT

        now = ts_now()
        # Check cache for a price within the last 24 hrs
        price_cache_entry = GlobalDBHandler().get_historical_price(
            from_asset=base,
            to_asset=quote,
            timestamp=now,
            max_seconds_distance=DAY_IN_SECONDS,
        )
        if price_cache_entry:
            return price_cache_entry.price, CurrentPriceOracle.FIAT

        # Use the xratescom query and save all prices in the cache
        price = None
        try:
            price_map = get_current_xratescom_exchange_rates(base)
            for quote_asset, quote_price in price_map.items():
                if quote_asset == quote:
                    # if the quote asset price is found return it
                    price = quote_price

                GlobalDBHandler().add_historical_prices(entries=[HistoricalPrice(
                    from_asset=base,
                    to_asset=quote_asset,
                    source=HistoricalPriceOracle.XRATESCOM,
                    timestamp=timestamp_to_daystart_timestamp(now),
                    price=quote_price,
                )])

            if price:  # the quote asset may not be found
                return price, CurrentPriceOracle.FIAT
        except RemoteError:
            pass  # price remains None

        # query backup api
        price = _query_currency_converterapi(base, quote)
        if price is not None:
            return price, CurrentPriceOracle.FIAT

        # Check cache
        price_cache_entry = GlobalDBHandler().get_historical_price(
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
