from __future__ import unicode_literals  # isort:skip

import logging
from enum import Enum
from pathlib import Path
import operator
from typing import Any, TYPE_CHECKING, Dict, Iterable, List, NamedTuple, Optional, Tuple, Union

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.defi.curve_pools import get_curve_pools
from rotkehlchen.chain.ethereum.defi.price import handle_defi_price_query
from rotkehlchen.chain.ethereum.utils import multicall_2, token_normalized_value_decimals
from rotkehlchen.constants import CURRENCYCONVERTER_API_KEY, ZERO
from rotkehlchen.constants.assets import (
    A_3CRV,
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
    A_WETH,
)
from rotkehlchen.constants.ethereum import CURVE_POOL_ABI, UNISWAP_V2_LP_ABI, YEARN_VAULT_V2_ABI
from rotkehlchen.constants.timing import DAY_IN_SECONDS, MONTH_IN_SECONDS
from rotkehlchen.errors import (
    DeserializationError,
    PriceQueryUnsupportedAsset,
    RemoteError,
    UnableToDecryptRemoteData,
    UnknownAsset,
)
from rotkehlchen.externalapis.xratescom import (
    get_current_xratescom_exchange_rates,
    get_historical_xratescom_exchange_rates,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.typing import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import (
    CURVE_POOL_PROTOCOL,
    KnownProtocolsAssets,
    Price,
    Timestamp,
    UNISWAP_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
)
from rotkehlchen.utils.misc import timestamp_to_daystart_timestamp, ts_now
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CURRENT_PRICE_CACHE_SECS = 300  # 5 mins

ASSETS_UNDERLYING_BTC = (
    A_YV1_RENWSBTC,
    A_FARM_CRVRENWBTC,
    A_FARM_RENBTC,
    A_FARM_WBTC,
    A_CRV_RENWBTC,
    A_CRVP_RENWSBTC,
)


CurrentPriceOracleInstance = Union['Coingecko', 'Cryptocompare']


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
    if token.protocol == UNISWAP_PROTOCOL:
        price = Inquirer().find_uniswap_v2_lp_price(token)
    elif token.protocol == CURVE_POOL_PROTOCOL:
        price = Inquirer().find_curve_pool_price(token)
    elif token.protocol == YEARN_VAULTS_V2_PROTOCOL:
        price = Inquirer().find_yearn_price(token)

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

    custom_token = GlobalDBHandler().get_ethereum_token(token.ethereum_address)
    if custom_token and custom_token.underlying_tokens is not None:
        usd_price = ZERO
        for underlying_token in custom_token.underlying_tokens:
            token = EthereumToken(underlying_token.address)
            usd_price += Inquirer().find_usd_price(token) * underlying_token.weight
        if usd_price != Price(ZERO):
            price = Price(usd_price)

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
    special_tokens: List[EthereumToken]

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
        Inquirer.special_tokens = [
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
            A_3CRV,
        ]
        return Inquirer.__instance

    @staticmethod
    def inject_ethereum(ethereum: 'EthereumManager') -> None:
        Inquirer()._ethereum = ethereum

    @staticmethod
    def get_cached_current_price_entry(cache_key: Tuple[Asset, Asset]) -> Optional[CachedPriceEntry]:  # noqa: E501
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
            cache = instance.get_cached_current_price_entry(cache_key=(from_asset, to_asset))
            if cache is not None:
                return cache.price

        oracle_price = instance._query_oracle_instances(from_asset=from_asset, to_asset=to_asset)
        return oracle_price

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
            cache = instance.get_cached_current_price_entry(cache_key=cache_key)
            if cache is not None:
                return cache.price

        if asset.is_fiat():
            try:
                return instance._query_fiat_pair(base=asset, quote=A_USD)
            except RemoteError:
                pass  # continue, a price can be found by one of the oracles (CC for example)

        # Try and check if it is an ethereum token with specified protocol or underlying tokens
        is_known_protocol = False
        underlying_tokens = None
        try:
            token = EthereumToken.from_asset(asset)
            if token is not None:
                if token.protocol is not None:
                    is_known_protocol = token.protocol in KnownProtocolsAssets
                underlying_tokens = GlobalDBHandler().get_ethereum_token(  # type: ignore
                    token.ethereum_address,
                ).underlying_tokens
        except UnknownAsset:
            pass

        # Check if it is a special token
        if asset in instance.special_tokens:
            ethereum = instance._ethereum
            assert ethereum, 'Inquirer should never be called before the injection of ethereum'
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

        if is_known_protocol is True or underlying_tokens is not None:
            assert token is not None
            result = get_underlying_asset_price(token)
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
            )
            return usd_price

        return instance._query_oracle_instances(from_asset=asset, to_asset=A_USD)

    def find_uniswap_v2_lp_price(
        self,
        token: EthereumToken,
    ) -> Optional[Price]:
        """
        Calculate the price for a uniswap v2 LP token. That is
        value = (Total value of liquidity pool) / (Current suply of LP tokens)
        We need:
        - Price of token 0
        - Price of token 1
        - Pooled amount of token 0
        - Pooled amount of token 1
        - Total supply of of pool token
        """
        assert self._ethereum is not None, 'Inquirer ethereum manager should have been initialized'  # noqa: E501

        address = token.ethereum_address
        contract = EthereumContract(address=address, abi=UNISWAP_V2_LP_ABI, deployed_block=0)
        methods = ['token0', 'token1', 'totalSupply', 'getReserves', 'decimals']
        try:
            output = multicall_2(
                ethereum=self._ethereum,
                require_success=True,
                calls=[(address, contract.encode(method_name=method)) for method in methods],
            )
        except RemoteError as e:
            log.error(
                f'Remote error calling multicall contract for uniswap v2 lp '
                f'token {token.ethereum_address} properties: {str(e)}',
            )
            return None

        # decode output
        decoded = []
        for (method_output, method_name) in zip(output, methods):
            if method_output[0] and len(method_output[1]) != 0:
                decoded_method = contract.decode(method_output[1], method_name)
                if len(decoded_method) == 1:
                    decoded.append(decoded_method[0])
                else:
                    decoded.append(decoded_method)
            else:
                log.debug(
                    f'Multicall to Uniswap V2 LP failed to fetch field {method_name} '
                    f'for token {token.ethereum_address}',
                )
                return None

        try:
            token0 = EthereumToken(decoded[0])
            token1 = EthereumToken(decoded[1])
        except UnknownAsset:
            return None

        try:
            token0_supply = FVal(decoded[3][0] * 10**-token0.decimals)
            token1_supply = FVal(decoded[3][1] * 10**-token1.decimals)
            total_supply = FVal(decoded[2] * 10 ** - decoded[4])
        except ValueError as e:
            log.debug(
                f'Failed to deserialize token amounts for token {address} '
                f'with values {str(decoded)}. f{str(e)}',
            )
            return None
        token0_price = self.find_usd_price(token0)
        token1_price = self.find_usd_price(token1)

        if ZERO in (token0_price, token1_price):
            log.debug(
                f'Couldnt retrieve non zero price information for tokens {token0}, {token1} '
                f'with result {token0_price}, {token1_price}',
            )
        numerator = (token0_supply * token0_price + token1_supply * token1_price)
        share_value = numerator / total_supply
        return Price(share_value)

    def find_curve_pool_price(
        self,
        lp_token: EthereumToken,
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

        pools = get_curve_pools()
        if lp_token.ethereum_address not in pools:
            return None
        pool = pools[lp_token.ethereum_address]
        tokens = []
        # Translate addresses to tokens
        try:
            for asset in pool.assets:
                if asset == '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE':
                    tokens.append(A_WETH)
                else:
                    tokens.append(EthereumToken(asset))
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
        contract = EthereumContract(
            address=pool.pool_address,
            abi=CURVE_POOL_ABI,
            deployed_block=0,
        )
        calls = [(pool.pool_address, contract.encode(method_name='get_virtual_price'))]
        calls += [
            (pool.pool_address, contract.encode(method_name='balances', arguments=[i]))
            for i in range(len(pool.assets))
        ]
        output = multicall_2(
            ethereum=self._ethereum,
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
        virtual_price_decoded = contract.decode(output[0][1], 'get_virtual_price')
        if not _check_curve_contract_call(virtual_price_decoded):
            log.debug(f'Failed to decode get_virtual_price while finding curve price. {output}')
            return None
        data.append(FVal(virtual_price_decoded[0]))
        for i in range(len(pool.assets)):
            amount_decoded = contract.decode(output[i + 1][1], 'balances', arguments=[i])
            if not _check_curve_contract_call(amount_decoded):
                log.debug(f'Failed to decode balances {i} while finding curve price. {output}')
                return None
            amount = amount_decoded[0]
            normalized_amount = token_normalized_value_decimals(amount, tokens[i].decimals)
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
        weights = map(lambda x: data[x + 1] * prices[x] / total_assets_price, range(len(tokens)))
        assets_price = FVal(sum(map(operator.mul, weights, prices)))
        return (assets_price * FVal(data[0])) / (10 ** lp_token.decimals)

    def find_yearn_price(
        self,
        token: EthereumToken,
    ) -> Optional[Price]:
        """
        Query price for a yearn vault v2 token using the pricePerShare method
        and the price of the underlying token.
        """
        assert self._ethereum is not None, 'Inquirer ethereum manager should have been initialized'  # noqa: E501

        maybe_underlying_token = GlobalDBHandler().fetch_underlying_tokens(token.ethereum_address)
        if maybe_underlying_token is None or len(maybe_underlying_token) != 1:
            log.error(f'Yearn vault token {token} without an underlying asset')
            return None

        underlying_token = EthereumToken(maybe_underlying_token[0].address)
        underlying_token_price = self.find_usd_price(underlying_token)
        # Get the price per share from the yearn contract
        contract = EthereumContract(
            address=token.ethereum_address,
            abi=YEARN_VAULT_V2_ABI,
            deployed_block=0,
        )
        output = multicall_2(
            ethereum=self._ethereum,
            require_success=True,
            calls=[(token.ethereum_address, contract.encode(method_name='pricePerShare'))],
        )
        if isinstance(output, list) and len(output) != 0 and output[0][0] is True:
            price_per_share = contract.decode(output[0][1], 'pricePerShare')
            if len(price_per_share) != 0:
                return price_per_share[0] * underlying_token_price
            log.error(f'Failed to decode pricePerShare for yearn vault v2 token {token}')
            # will return None right below
        log.error(
            f'Error to call multicall for price on Yearn vault v2 token {token} '
            f'with output {output}.',
        )
        return None

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
    def _query_fiat_pair(base: Asset, quote: Asset) -> Price:
        """Queries the current price between two fiat assets

        If a current price is not found but a cached price within 30 days is found
        then that one is used.

        May raise RemoteError if a price can not be found
        """
        if base == quote:
            return Price(FVal('1'))

        now = ts_now()
        # Check cache for a price within the last 24 hrs
        price_cache_entry = GlobalDBHandler().get_historical_price(
            from_asset=base,
            to_asset=quote,
            timestamp=now,
            max_seconds_distance=DAY_IN_SECONDS,
        )
        if price_cache_entry:
            return price_cache_entry.price

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
                return price
        except RemoteError:
            pass  # price remains None

        # query backup api
        price = _query_currency_converterapi(base, quote)
        if price is not None:
            return price

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
            return price_cache_entry.price

        # else
        raise RemoteError(
            f'Could not find a current {base.identifier} price for {quote.identifier}',
        )
