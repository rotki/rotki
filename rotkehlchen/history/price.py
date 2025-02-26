import logging
from collections import defaultdict
from collections.abc import Mapping, Sequence
from contextlib import suppress
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.polygon_pos.constants import POLYGON_POS_POL_HARDFORK
from rotkehlchen.constants import HOUR_IN_SECONDS, ONE
from rotkehlchen.constants.assets import (
    A_ETH,
    A_ETH2,
    A_EUR,
    A_KFEE,
    A_POLYGON_POS_MATIC,
    A_USD,
)
from rotkehlchen.constants.prices import ZERO_PRICE
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


def query_usd_price_or_use_default(
        asset: Asset,
        time: Timestamp,
        default_value: FVal,
        location: str,
) -> Price:
    try:
        usd_price = PriceHistorian().query_historical_price(
            from_asset=asset,
            to_asset=A_USD,
            timestamp=time,
        )
    except (RemoteError, NoPriceForGivenTimestamp):
        log.error(
            f'Could not query usd price for {asset.identifier} and time {time} '
            f'when processing {location}. Assuming price of ${default_value!s}',
        )
        usd_price = Price(default_value)

    return usd_price


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
    def get_price_for_special_asset(
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
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

        May raise:
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the external service.
        """
        if from_asset == A_ETH2:
            return PriceHistorian.query_historical_price(
                from_asset=A_ETH,
                to_asset=to_asset,
                timestamp=timestamp,
            )

        if from_asset == A_KFEE:
            # For KFEE the price is fixed at 0.01$
            usd_price = Price(FVal(0.01))
            if to_asset == A_USD:
                return usd_price

            price_mapping = PriceHistorian().query_historical_price(
                from_asset=A_USD,
                to_asset=to_asset,
                timestamp=timestamp,
            )
            return Price(usd_price * price_mapping)

        if from_asset == A_POLYGON_POS_MATIC and timestamp > POLYGON_POS_POL_HARDFORK:
            return PriceHistorian.query_historical_price(
                from_asset=Asset('eip155:1/erc20:0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6'),  # POL token  # noqa: E501,
                to_asset=to_asset,
                timestamp=timestamp,
            )

        if GlobalDBHandler.asset_in_collection(collection_id=240, asset_id=from_asset.identifier):  # part of the EURe collection # noqa: E501  # todo: Super hacky. Figure out a way to generalize
            return PriceHistorian.query_historical_price(
                from_asset=A_EUR,
                to_asset=to_asset,
                timestamp=timestamp,
            )

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
        price_historian = PriceHistorian()
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
                assets_price[asset][timestamp] = price_historian.query_historical_price(
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
