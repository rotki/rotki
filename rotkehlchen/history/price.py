import logging
from collections import defaultdict
from collections.abc import Mapping, Sequence
from contextlib import suppress
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2, CPT_UNISWAP_V3
from rotkehlchen.chain.evm.decoding.uniswap.v3.utils import get_uniswap_v3_position_price
from rotkehlchen.chain.evm.utils import lp_price_from_uniswaplike_pool_contract
from rotkehlchen.constants import HOUR_IN_SECONDS, ONE
from rotkehlchen.constants.assets import (
    A_ETH,
    A_ETH2,
    A_EUR,
    A_KFEE,
    A_USD,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp

from .types import HistoricalPrice, HistoricalPriceOracle, HistoricalPriceOracleInstance

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
    from rotkehlchen.externalapis.alchemy import Alchemy
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.externalapis.defillama import Defillama
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_price_or_use_default(
        asset: Asset,
        time: Timestamp,
        default_value: FVal,
        location: str,
) -> Price:
    """Query price in the user's main currency, or use default if unavailable"""
    main_currency = CachedSettings().main_currency
    try:
        price = PriceHistorian().query_historical_price(
            from_asset=asset,
            to_asset=main_currency,
            timestamp=time,
        )
    except (RemoteError, NoPriceForGivenTimestamp):
        log.error(
            f'Could not query price for {asset.identifier} and time {time} in {main_currency=} '
            f'when processing {location}. Assuming price of {default_value!s}',
        )
        price = Price(default_value)

    return price


class PriceHistorian:
    __instance: Optional['PriceHistorian'] = None
    _cryptocompare: 'Cryptocompare'
    _coingecko: 'Coingecko'
    _defillama: 'Defillama'
    _alchemy: 'Alchemy'
    _uniswapv2: 'UniswapV2Oracle'
    _uniswapv3: 'UniswapV3Oracle'
    _oracles: Sequence[HistoricalPriceOracle] | None = None
    _oracle_instances: list[HistoricalPriceOracleInstance] | None = None

    def __new__(
            cls,
            data_directory: Path | None = None,
            cryptocompare: Optional['Cryptocompare'] = None,
            coingecko: Optional['Coingecko'] = None,
            defillama: Optional['Defillama'] = None,
            alchemy: Optional['Alchemy'] = None,
            uniswapv2: Optional['UniswapV2Oracle'] = None,
            uniswapv3: Optional['UniswapV3Oracle'] = None,
    ) -> 'PriceHistorian':
        if PriceHistorian.__instance is not None:
            return PriceHistorian.__instance

        error_msg = 'arguments should be given at the first instantiation'
        assert data_directory, error_msg
        assert cryptocompare, error_msg
        assert coingecko, error_msg
        assert defillama, error_msg
        assert alchemy, error_msg
        assert uniswapv2, error_msg
        assert uniswapv3, error_msg

        PriceHistorian.__instance = object.__new__(cls)
        PriceHistorian._cryptocompare = cryptocompare
        PriceHistorian._coingecko = coingecko
        PriceHistorian._defillama = defillama
        PriceHistorian._alchemy = alchemy
        PriceHistorian._uniswapv2 = uniswapv2
        PriceHistorian._uniswapv3 = uniswapv3

        return PriceHistorian.__instance

    @staticmethod
    def set_oracles_order(oracles: Sequence[HistoricalPriceOracle]) -> None:
        assert len(oracles) != 0 and len(oracles) == len(set(oracles)), (
            "Oracles can't be empty or have repeated items"
        )
        instance = PriceHistorian()
        instance._oracles = oracles
        instance._oracle_instances = [getattr(instance, f'_{oracle!s}') for oracle in oracles]

    @staticmethod
    def _get_cached_price_or_query(
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            max_seconds_distance: int | None,
    ) -> Price | None:
        """Helper method to get price from cache if `max_seconds_distance`
        is given, otherwise query normally.
        """
        if from_asset == to_asset:
            return Price(ONE)

        if max_seconds_distance is not None:
            cached_price_entry = GlobalDBHandler.get_historical_price(
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
                max_seconds_distance=max_seconds_distance,
            )
            # we return None here by design to avoid making remote queries in cache-only mode
            return cached_price_entry.price if cached_price_entry is not None else None
        else:
            return PriceHistorian.query_historical_price(
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )

    @staticmethod
    def get_price_for_special_asset(
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            max_seconds_distance: int | None = None,
    ) -> Price | None:
        """
        Query the historical price on `timestamp` for `from_asset` in `to_asset`
        for the case where `from_asset` needs a special handling.

        Can return None if the from asset is not in the list of special cases

        Args:
            from_asset: The ticker symbol of the asset for which we want to know
                        the price.
            to_asset: The ticker symbol of the asset against which we want to
                      know the price.
            timestamp: The timestamp at which to query the price
            max_seconds_distance: Maximum time distance for cache lookups

        May raise:
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the external service.
        """
        if from_asset == A_ETH2:
            return PriceHistorian._get_cached_price_or_query(
                from_asset=A_ETH,
                to_asset=to_asset,
                timestamp=timestamp,
                max_seconds_distance=max_seconds_distance,
            )

        if from_asset == A_KFEE:
            # For KFEE the price is fixed at 0.01$
            usd_price = Price(FVal(0.01))
            if to_asset == A_USD:
                return usd_price

            usd_to_target_price = PriceHistorian._get_cached_price_or_query(
                from_asset=A_USD,
                to_asset=to_asset,
                timestamp=timestamp,
                max_seconds_distance=max_seconds_distance,
            )
            return Price(usd_price * usd_to_target_price) if usd_to_target_price is not None else None  # noqa: E501

        if GlobalDBHandler.asset_in_collection(collection_id=240, asset_id=from_asset.identifier):  # part of the EURe collection # noqa: E501  # todo: Super hacky. Figure out a way to generalize
            return PriceHistorian._get_cached_price_or_query(
                from_asset=A_EUR,
                to_asset=to_asset,
                timestamp=timestamp,
                max_seconds_distance=max_seconds_distance,
            )

        if from_asset.is_evm_token() and (pool_token := from_asset.resolve_to_evm_token()).protocol in {CPT_UNISWAP_V2, CPT_UNISWAP_V3}:  # noqa: E501
            if max_seconds_distance is not None:
                cached_price_entry = GlobalDBHandler.get_historical_price(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    timestamp=timestamp,
                    max_seconds_distance=max_seconds_distance,
                )
                return cached_price_entry.price if cached_price_entry is not None else None
            else:
                try:
                    return PriceHistorian.query_uniswap_position_price(
                        pool_token=pool_token,
                        pool_token_amount=ONE,
                        to_asset=to_asset,
                        timestamp=timestamp,
                    )
                except (RemoteError, NoPriceForGivenTimestamp):
                    log.error(f'Could not query uniswap position price for {from_asset.identifier} and time {timestamp}.')  # noqa: E501
                    return None

        return None

    @staticmethod
    def query_historical_price(
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """
        Query the historical price on `timestamp` for `from_asset` in `to_asset`.
        So how much `to_asset` does 1 unit of `from_asset` cost.

        Args:
            from_asset: The ticker symbol of the asset for which we want to know
                        the price.
            to_asset: The ticker symbol of the asset against which we want to
                        know the price.
            timestamp: The timestamp at which to query the price

        May raise:
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the external service.
        """
        log.debug(
            'Querying historical price',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        if from_asset == to_asset:
            return Price(ONE)

        special_asset_price = PriceHistorian().get_price_for_special_asset(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        if special_asset_price is not None:
            return special_asset_price

        # Querying historical forex data is attempted first via the external apis
        # and then via any price oracle that has fiat to fiat.
        with suppress(UnknownAsset, WrongAssetType):
            from_asset = from_asset.resolve_to_fiat_asset()
            to_asset = to_asset.resolve_to_fiat_asset()
            price = Inquirer().query_historical_fiat_exchange_rates(
                from_fiat_currency=from_asset,
                to_fiat_currency=to_asset,
                timestamp=timestamp,
            )
            if price is not None:
                return price

        # try to get the price from the cache
        if (cached_price_entry := GlobalDBHandler.get_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            max_seconds_distance=HOUR_IN_SECONDS,
        )) is not None:
            return cached_price_entry.price

        # else cryptocompare also has historical fiat to fiat data
        instance = PriceHistorian()
        oracles = instance._oracles
        oracle_instances = instance._oracle_instances
        assert oracles is not None and oracle_instances is not None, (
            'PriceHistorian should never be called before setting the oracles'
        )
        rate_limited = False
        for oracle, oracle_instance in zip(oracles, oracle_instances, strict=True):
            can_query_history = oracle_instance.can_query_history(
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )
            if can_query_history is False:
                continue

            try:
                price = oracle_instance.query_historical_price(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    timestamp=timestamp,
                )
            except (
                PriceQueryUnsupportedAsset,
                NoPriceForGivenTimestamp,
                UnknownAsset,
                WrongAssetType,
            ):
                continue
            except RemoteError as e:
                # Raise the flag if any of the services was rate limited
                rate_limited = (
                    rate_limited is True or
                    e.error_code == HTTPStatus.TOO_MANY_REQUESTS
                )
                continue

            log.debug(
                f'Historical price oracle {oracle} got price',
                price=price,
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )
            GlobalDBHandler.add_historical_prices([HistoricalPrice(
                from_asset=from_asset,
                to_asset=to_asset,
                source=oracle,
                timestamp=timestamp,
                price=price,
            )])
            return price

        raise NoPriceForGivenTimestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            time=timestamp,
            rate_limited=rate_limited,
        )

    @staticmethod
    def query_multiple_prices(
            assets_timestamp: list[tuple[Asset, Timestamp]],
            target_asset: Asset,
            msg_aggregator: 'MessagesAggregator',
    ) -> Mapping[Asset, Mapping[Timestamp, Price]]:
        """Return the price of the assets at the given timestamps in the target
        asset currency.
        """
        log.debug(
            f'Querying the historical {target_asset.identifier} price of these assets: '
            f'{", ".join(f"{asset.identifier} at {ts}" for asset, ts in assets_timestamp)}',
            assets_timestamp=assets_timestamp,
        )
        assets_price: defaultdict[Asset, defaultdict] = defaultdict(
            lambda: defaultdict(lambda: ZERO_PRICE),
        )
        send_ws_every_prices = msg_aggregator.how_many_events_per_ws(
            total_events=(total_events := len(assets_timestamp)),
        )
        for idx, (asset, timestamp) in enumerate(assets_timestamp):
            if idx % send_ws_every_prices == 0:
                msg_aggregator.add_message(
                    message_type=WSMessageType.PROGRESS_UPDATES,
                    data={
                        'total': total_events,
                        'processed': idx,
                        'subtype': str(ProgressUpdateSubType.MULTIPLE_PRICES_QUERY_STATUS),
                    },
                )

            try:
                assets_price[asset][timestamp] = PriceHistorian.query_historical_price(
                    from_asset=asset,
                    to_asset=target_asset,
                    timestamp=timestamp,
                )
            except (RemoteError, NoPriceForGivenTimestamp) as e:
                log.warning(
                    f'Could not query the historical {target_asset.identifier} price for '
                    f'{asset.identifier} at time {timestamp} due to: {e!s}. Skipping',
                )
                continue

        msg_aggregator.add_message(
            message_type=WSMessageType.PROGRESS_UPDATES,
            data={
                'total': total_events,
                'processed': total_events,
                'subtype': str(ProgressUpdateSubType.MULTIPLE_PRICES_QUERY_STATUS),
            },
        )

        return assets_price

    @staticmethod
    def query_uniswap_position_price(
            pool_token: EvmToken,
            pool_token_amount: FVal,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """Return the uniswap position value at the given timestamp. Works both with V2 and V3.

        Note: This function should only be called for a Uniswap liquidity token.

        May raise:
            RemoteError: If an unexpected response is returned on get_blocknumber_by_time function
            NoPriceForGivenTimestamp if we can't find a price for the asset in the given timestamp
        """
        evm_inquirer = Inquirer.get_evm_manager(chain_id=pool_token.chain_id).node_inquirer
        block_number = evm_inquirer.get_blocknumber_by_time(timestamp)
        if pool_token.protocol == CPT_UNISWAP_V2:
            if (pool_price := lp_price_from_uniswaplike_pool_contract(
                evm_inquirer=evm_inquirer,
                token=pool_token,
                price_func=lambda asset: PriceHistorian.query_historical_price(asset, to_asset, timestamp),  # noqa: E501
                block_identifier=block_number,
            )) is not None:
                return Price(pool_token_amount * pool_price)

            return ZERO_PRICE

        return get_uniswap_v3_position_price(
            token=pool_token,
            evm_inquirer=evm_inquirer,
            block_identifier=block_number,
            price_func=lambda asset: PriceHistorian.query_historical_price(asset, to_asset, timestamp),  # noqa: E501
        )
