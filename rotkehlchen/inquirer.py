from __future__ import unicode_literals  # isort:skip

import logging
from enum import Enum
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List, NamedTuple, Optional, Tuple, Union

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.defi.price import handle_defi_price_query
from rotkehlchen.constants import CURRENCYCONVERTER_API_KEY, ZERO
from rotkehlchen.constants.assets import (
    A_ALINK_V1,
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
    A_TUSD,
    A_USD,
    A_USDC,
    A_USDT,
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
from rotkehlchen.errors import (
    DeserializationError,
    PriceQueryUnsupportedAsset,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.externalapis.xratescom import (
    get_current_xratescom_exchange_rates,
    get_historical_xratescom_exchange_rates,
)
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_price
from rotkehlchen.typing import Price, Timestamp
from rotkehlchen.utils.misc import get_or_make_price_history_dir, timestamp_to_date, ts_now
from rotkehlchen.utils.network import request_get_dict
from rotkehlchen.utils.serialization import jsonloads_dict, rlk_jsondumps

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CURRENT_PRICE_CACHE_SECS = 300  # 5 mins

SPECIAL_TOKENS = (
    A_YV1_DAIUSDCTBUSD,
    A_CRVP_DAIUSDCTBUSD,
    A_CRVP_DAIUSDCTTUSD,
    A_YV1_DAIUSDCTTUSD,
    A_YV1_DAIUSDCTTUSD,
    A_CRVP_RENWSBTC,
    A_YV1_RENWSBTC,
    A_CRV_RENWBTC,
    A_CRV_YPAX,
    A_CRV_GUSD,
    A_CRV_3CRV,
    A_YV1_3CRV,
    A_CRV_3CRVSUSD,
    A_YV1_ALINK,
    A_YV1_DAI,
    A_YV1_WETH,
    A_YV1_YFI,
    A_YV1_USDT,
    A_YV1_USDC,
    A_YV1_TUSD,
    A_YV1_GUSD,
    A_FARM_USDC,
    A_FARM_USDT,
    A_FARM_DAI,
    A_FARM_TUSD,
    A_FARM_WETH,
    A_FARM_WBTC,
    A_FARM_RENBTC,
    A_FARM_CRVRENWBTC,
)

ASSETS_UNDERLYING_BTC = (
    A_YV1_RENWSBTC,
    A_FARM_CRVRENWBTC,
    A_FARM_RENBTC,
    A_FARM_WBTC,
    A_CRV_RENWBTC,
    A_CRVP_RENWSBTC,
)


CurrentPriceOracleInstance = Union['Coingecko', 'Cryptocompare']


class CurrentPriceOracle(Enum):
    """Supported oracles for querying current prices
    """
    COINGECKO = 1
    CRYPTOCOMPARE = 2

    def __str__(self) -> str:
        if self == CurrentPriceOracle.COINGECKO:
            return 'coingecko'
        if self == CurrentPriceOracle.CRYPTOCOMPARE:
            return 'cryptocompare'
        raise AssertionError(f'Unexpected CurrentPriceOracle: {self}')

    def serialize(self) -> str:
        return str(self)

    @classmethod
    def deserialize(cls, name: str) -> 'CurrentPriceOracle':
        if name == 'coingecko':
            return cls.COINGECKO
        if name == 'cryptocompare':
            return cls.CRYPTOCOMPARE
        raise DeserializationError(f'Failed to deserialize current price oracle: {name}')


DEFAULT_CURRENT_PRICE_ORACLES_ORDER = [
    CurrentPriceOracle.COINGECKO,
    CurrentPriceOracle.CRYPTOCOMPARE,
]


def get_underlying_asset_price(token: EthereumToken) -> Optional[Price]:
    """Gets the underlying asset price for the given ethereum token

    TODO: This should be eventually pulled from the assets DB. All of these
    need to be updated, to contain proper protocol, and underlying assets.

    This function is neither in inquirer.py or chain/ethereum/defi.py
    due to recursive import problems
    """
    price = None
    if token == A_YV1_ALINK:
        price = Inquirer().find_usd_price(A_ALINK_V1)
    elif token == A_YV1_GUSD:
        price = Inquirer().find_usd_price(A_GUSD)
    elif token in (A_YV1_DAI, A_FARM_DAI):
        price = Inquirer().find_usd_price(A_DAI)
    elif token in (A_FARM_WETH, A_YV1_WETH):
        price = Inquirer().find_usd_price(A_ETH)
    elif token == A_YV1_YFI:
        price = Inquirer().find_usd_price(A_YFI)
    elif token in (A_FARM_USDT, A_YV1_USDT):
        price = Inquirer().find_usd_price(A_USDT)
    elif token in (A_FARM_USDC, A_YV1_USDC):
        price = Inquirer().find_usd_price(A_USDC)
    elif token in (A_FARM_TUSD, A_YV1_TUSD):
        price = Inquirer().find_usd_price(A_TUSD)
    elif token in ASSETS_UNDERLYING_BTC:
        price = Inquirer().find_usd_price(A_BTC)

    return price


def _query_currency_converterapi(base: Asset, quote: Asset) -> Optional[Price]:
    assert base.is_fiat(), 'fiat currency should have been provided'
    assert quote.is_fiat(), 'fiat currency should have been provided'
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


class Inquirer():
    __instance: Optional['Inquirer'] = None
    _cached_forex_data: Dict
    _cached_current_price: Dict  # Can't use CacheableMixIn due to Singleton
    _data_directory: Path
    _cryptocompare: 'Cryptocompare'
    _coingecko: 'Coingecko'
    _ethereum: Optional['EthereumManager'] = None
    _oracles: Optional[List[CurrentPriceOracle]] = None
    _oracle_instances: Optional[List[CurrentPriceOracleInstance]] = None

    def __new__(
            cls,
            data_dir: Path = None,
            cryptocompare: 'Cryptocompare' = None,
            coingecko: 'Coingecko' = None,
    ) -> 'Inquirer':
        if Inquirer.__instance is not None:
            return Inquirer.__instance

        assert data_dir, 'arguments should be given at the first instantiation'
        assert cryptocompare, 'arguments should be given at the first instantiation'
        assert coingecko, 'arguments should be given at the first instantiation'

        Inquirer.__instance = object.__new__(cls)

        Inquirer.__instance._data_directory = data_dir
        Inquirer._cryptocompare = cryptocompare
        Inquirer._coingecko = coingecko
        Inquirer._cached_current_price = {}
        # Make price history directory if it does not exist
        price_history_dir = get_or_make_price_history_dir(data_dir)
        filename = price_history_dir / 'price_history_forex.json'
        try:
            with open(filename, 'r') as f:
                # we know price_history_forex contains a dict
                data = jsonloads_dict(f.read())
                Inquirer.__instance._cached_forex_data = data
        except (OSError, JSONDecodeError):
            Inquirer.__instance._cached_forex_data = {}

        return Inquirer.__instance

    @staticmethod
    def inject_ethereum(ethereum: 'EthereumManager') -> None:
        Inquirer()._ethereum = ethereum

    @staticmethod
    def get_cached_price_entry(cache_key: Tuple[Asset, Asset]) -> Optional[CachedPriceEntry]:
        cache = Inquirer()._cached_current_price.get(cache_key, None)
        if cache is None or ts_now() - cache.time > CURRENT_PRICE_CACHE_SECS:
            return None

        return cache

    @staticmethod
    def set_oracles_order(oracles: List[CurrentPriceOracle]) -> None:
        assert len(oracles) != 0 and len(oracles) == len(set(oracles)), (
            'Oracles can\'t be empty or have repeated items'
        )
        instance = Inquirer()
        instance._oracles = oracles
        instance._oracle_instances = [getattr(instance, f'_{str(oracle)}') for oracle in oracles]

    @staticmethod
    def _query_oracle_instances(
            from_asset: Asset,
            to_asset: Asset,
    ) -> Price:
        instance = Inquirer()
        cache_key = (from_asset, to_asset)
        oracles = instance._oracles
        oracle_instances = instance._oracle_instances
        assert isinstance(oracles, list) and isinstance(oracle_instances, list), (
            'Inquirer should never be called before the setting the oracles'
        )
        price = Price(ZERO)
        for oracle, oracle_instance in zip(oracles, oracle_instances):
            if oracle_instance.rate_limited_in_last() is True:
                continue

            try:
                price = oracle_instance.query_current_price(
                    from_asset=from_asset,
                    to_asset=to_asset,
                )
            except (PriceQueryUnsupportedAsset, RemoteError) as e:
                log.error(
                    f'Current price oracle {oracle} failed to request {to_asset.identifier} '
                    f'price for {from_asset.identifier} due to: {str(e)}.',
                )
                continue

            if price != Price(ZERO):
                log.debug(
                    f'Current price oracle {oracle} got price',
                    from_asset=from_asset,
                    to_asset=to_asset,
                    price=price,
                )
                break

        Inquirer._cached_current_price[cache_key] = CachedPriceEntry(price=price, time=ts_now())
        return price

    @staticmethod
    def find_price(
            from_asset: Asset,
            to_asset: Asset,
            ignore_cache: bool = False,
    ) -> Price:
        """Returns the current price of 'from_asset' in 'to_asset' valuation.
        NB: prices for special symbols in any currency but USD are not supported.

        Returns Price(ZERO) if all options have been exhausted and errors are logged in the logs
        """
        if from_asset == to_asset:
            return Price(FVal('1'))

        instance = Inquirer()
        if to_asset == A_USD:
            return instance.find_usd_price(asset=from_asset, ignore_cache=ignore_cache)

        if ignore_cache is False:
            cache = instance.get_cached_price_entry(cache_key=(from_asset, to_asset))
            if cache is not None:
                return cache.price

        return instance._query_oracle_instances(from_asset=from_asset, to_asset=to_asset)

    @staticmethod
    def find_usd_price(
            asset: Asset,
            ignore_cache: bool = False,
    ) -> Price:
        """Returns the current USD price of the asset

        Returns Price(ZERO) if all options have been exhausted and errors are logged in the logs
        """
        if asset == A_USD:
            return Price(FVal(1))

        instance = Inquirer()
        cache_key = (asset, A_USD)
        if ignore_cache is False:
            cache = instance.get_cached_price_entry(cache_key=cache_key)
            if cache is not None:
                return cache.price

        if asset.is_fiat():
            try:
                return instance._query_fiat_pair(base=asset, quote=A_USD)
            except RemoteError:
                pass  # continue, a price can be found by one of the oracles (CC for example)

        if asset in SPECIAL_TOKENS:
            ethereum = instance._ethereum
            assert ethereum, 'Inquirer should never be called before the injection of ethereum'
            token = EthereumToken.from_asset(asset)
            assert token, 'all assets in special tokens are already ethereum tokens'
            underlying_asset_price = get_underlying_asset_price(token)
            usd_price = handle_defi_price_query(
                ethereum=ethereum,
                token=token,
                underlying_asset_price=underlying_asset_price,
            )
            if usd_price is None:
                price = Price(ZERO)
            else:
                price = Price(usd_price)

            Inquirer._cached_current_price[cache_key] = CachedPriceEntry(price=price, time=ts_now())  # noqa: E501
            return price

        return instance._query_oracle_instances(from_asset=asset, to_asset=A_USD)

    @staticmethod
    def get_fiat_usd_exchange_rates(currencies: Iterable[Asset]) -> Dict[Asset, Price]:
        """Gets the USD exchange rate of any of the given assets

        In case of failure to query a rate it's returned as zero"""
        rates = {A_USD: Price(FVal(1))}
        for currency in currencies:
            try:
                rates[currency] = Inquirer()._query_fiat_pair(A_USD, currency)
            except RemoteError:
                rates[currency] = Price(ZERO)

        return rates

    @staticmethod
    def query_historical_fiat_exchange_rates(
            from_fiat_currency: Asset,
            to_fiat_currency: Asset,
            timestamp: Timestamp,
    ) -> Optional[Price]:
        assert from_fiat_currency.is_fiat(), 'fiat currency should have been provided'
        assert to_fiat_currency.is_fiat(), 'fiat currency should have been provided'
        date = timestamp_to_date(timestamp, formatstr='%Y-%m-%d')
        instance = Inquirer()
        rate = instance._get_cached_forex_data(date, from_fiat_currency, to_fiat_currency)
        if rate:
            return rate

        try:
            prices_map = get_historical_xratescom_exchange_rates(
                from_asset=from_fiat_currency,
                time=timestamp,
            )
        except RemoteError:
            return None

        # save all prices in cache
        if date not in instance._cached_forex_data:
            instance._cached_forex_data[date] = {}

        if from_fiat_currency not in instance._cached_forex_data[date]:
            instance._cached_forex_data[date][from_fiat_currency] = {}

        rate = None
        for asset, asset_price in prices_map.items():
            instance._cached_forex_data[date][from_fiat_currency][asset] = asset_price
            if asset == to_fiat_currency:
                rate = asset_price

        log.debug('Historical fiat exchange rate query succesful', rate=rate)
        return rate

    @staticmethod
    def _save_forex_rate(
            date: str,
            from_currency: Asset,
            to_currency: Asset,
            price: FVal,
    ) -> None:
        assert from_currency.is_fiat(), 'fiat currency should have been provided'
        assert to_currency.is_fiat(), 'fiat currency should have been provided'
        instance = Inquirer()
        if date not in instance._cached_forex_data:
            instance._cached_forex_data[date] = {}

        if from_currency not in instance._cached_forex_data[date]:
            instance._cached_forex_data[date][from_currency] = {}

        instance._cached_forex_data[date][from_currency][to_currency] = price
        instance.save_historical_forex_data()

    @staticmethod
    def _get_cached_forex_data(
            date: str,
            from_currency: Asset,
            to_currency: Asset,
    ) -> Optional[Price]:
        instance = Inquirer()
        rate = None
        if date in instance._cached_forex_data:
            if from_currency in instance._cached_forex_data[date]:
                rate = instance._cached_forex_data[date][from_currency].get(to_currency)
                if rate:
                    log.debug(
                        'Got cached forex rate',
                        from_currency=from_currency.identifier,
                        to_currency=to_currency.identifier,
                        rate=rate,
                    )
                    try:
                        rate = deserialize_price(rate)
                    except DeserializationError as e:
                        log.error(f'Could not read cached forex entry due to {str(e)}')

        return rate

    @staticmethod
    def save_historical_forex_data() -> None:
        instance = Inquirer()
        # Make price history directory if it does not exist
        price_history_dir = get_or_make_price_history_dir(instance._data_directory)
        filename = price_history_dir / 'price_history_forex.json'
        with open(filename, 'w') as outfile:
            outfile.write(rlk_jsondumps(instance._cached_forex_data))

    @staticmethod
    def _query_fiat_pair(base: Asset, quote: Asset) -> Price:
        """Queries the current price between two fiat assets

        If a current price is not found but a cached price within 30 days is found
        then that one is used.

        May raise RemoteError if a price can not be found
        """
        if base == quote:
            return Price(FVal('1'))

        instance = Inquirer()
        now = ts_now()
        date = timestamp_to_date(ts_now(), formatstr='%Y-%m-%d')
        price = instance._get_cached_forex_data(date, base, quote)
        if price:
            return price

        # Use the xratescom query and save all prices in the cache
        price = None
        try:
            price_map = get_current_xratescom_exchange_rates(base)
            for quote_asset, quote_price in price_map.items():
                if quote_asset == quote:
                    # if the quote asset price is found return it
                    price = quote_price
                    continue  # dont save cache here. Will be saved at the end
                instance._save_forex_rate(date, base, quote_asset, quote_price)
        except RemoteError:
            pass  # price remains None

        if price is None:
            price = _query_currency_converterapi(base, quote)

        if price is None:
            # Search the cache for any price in the last month
            for i in range(1, 31):
                now = Timestamp(now - Timestamp(86401))
                date = timestamp_to_date(now, formatstr='%Y-%m-%d')
                price = instance._get_cached_forex_data(date, base, quote)
                if price:
                    log.debug(
                        f'Could not query online apis for a fiat price. '
                        f'Used cached value from {i} days ago.',
                        base_currency=base.identifier,
                        quote_currency=quote.identifier,
                        price=price,
                    )
                    return price

            raise RemoteError(
                f'Could not find a current {base.identifier} price for {quote.identifier}',
            )

        instance._save_forex_rate(date, base, quote, price)
        return price
