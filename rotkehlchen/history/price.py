import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_date

from .typing import (
    DEFAULT_HISTORICAL_PRICE_ORACLE_ORDER,
    HistoricalPriceOracle,
    HistoricalPriceOracleInstance,
)

if TYPE_CHECKING:
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare

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
            f'Could not query usd price for {asset.identifier} and time {time}'
            f'when processing {location}. Assuming price of ${str(default_value)}',
        )
        usd_price = Price(default_value)

    return usd_price


def query_usd_price_zero_if_error(
        asset: Asset,
        time: Timestamp,
        location: str,
        msg_aggregator: MessagesAggregator,
) -> Price:
    try:
        usd_price = PriceHistorian().query_historical_price(
            from_asset=asset,
            to_asset=A_USD,
            timestamp=time,
        )
    except (RemoteError, NoPriceForGivenTimestamp):
        msg_aggregator.add_error(
            f'Could not query usd price for {asset.identifier} and time {time} '
            f'when processing {location}. Using zero price',
        )
        usd_price = Price(ZERO)

    return usd_price


class PriceHistorian():
    __instance: Optional['PriceHistorian'] = None
    _cryptocompare: 'Cryptocompare'
    _coingecko: 'Coingecko'
    _oracle_instances: List[Tuple[HistoricalPriceOracle, HistoricalPriceOracleInstance]]
    _oracle_order: Sequence[HistoricalPriceOracle]

    def __new__(
            cls,
            data_directory: Path = None,
            cryptocompare: 'Cryptocompare' = None,
            coingecko: 'Coingecko' = None,
            oracle_order: Sequence[HistoricalPriceOracle] = None,
    ) -> 'PriceHistorian':
        if PriceHistorian.__instance is not None:
            return PriceHistorian.__instance

        assert data_directory, 'arguments should be given at the first instantiation'
        assert cryptocompare, 'arguments should be given at the first instantiation'
        assert coingecko, 'arguments should be given at the first instantiation'

        if oracle_order is None:
            oracle_order = DEFAULT_HISTORICAL_PRICE_ORACLE_ORDER

        if set(oracle_order) != set(HistoricalPriceOracle):
            raise AssertionError('All historical price oracles are required')

        oracle_instances = cls.get_oracle_instances(
            oracle_order=oracle_order,
            cryptocompare=cryptocompare,
            coingecko=coingecko,
        )
        PriceHistorian.__instance = object.__new__(cls)
        PriceHistorian._cryptocompare = cryptocompare
        PriceHistorian._coingecko = coingecko
        PriceHistorian._oracle_instances = oracle_instances
        PriceHistorian._oracle_order = oracle_order

        return PriceHistorian.__instance

    @staticmethod
    def get_oracle_instances(
            oracle_order: Sequence[HistoricalPriceOracle],
            cryptocompare: 'Cryptocompare',
            coingecko: 'Coingecko',
    ) -> List[Tuple[HistoricalPriceOracle, HistoricalPriceOracleInstance]]:
        oracle_instances: List[Tuple[HistoricalPriceOracle, HistoricalPriceOracleInstance]]
        oracle_instances = []
        for oracle in oracle_order:
            if oracle == HistoricalPriceOracle.COINGECKO:
                oracle_instances.append((oracle, coingecko))
            elif oracle == HistoricalPriceOracle.CRYPTOCOMPARE:
                oracle_instances.append((oracle, cryptocompare))
            else:
                raise AssertionError(f'Unexpected HistoricalPriceOracle: {oracle}')

        return oracle_instances

    @staticmethod
    def set_oracle_order(oracle_order: Sequence[HistoricalPriceOracle]) -> None:
        if set(oracle_order) != set(HistoricalPriceOracle):
            raise AssertionError('All historical price oracles are required')

        oracle_instances = PriceHistorian().get_oracle_instances(
            oracle_order=oracle_order,
            cryptocompare=PriceHistorian()._cryptocompare,
            coingecko=PriceHistorian()._coingecko,
        )
        PriceHistorian()._oracle_order = oracle_order
        PriceHistorian()._oracle_instances = oracle_instances

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
            return Price(FVal('1'))

        is_from_fiat_to_fiat = from_asset.is_fiat() and to_asset.is_fiat()
        # Querying historical forex data is attempted first via exchangerates API,
        # and then via any price oracle that has fiat to fiat.
        if is_from_fiat_to_fiat:
            price = Inquirer().query_historical_fiat_exchange_rates(
                from_fiat_currency=from_asset,
                to_fiat_currency=to_asset,
                timestamp=timestamp,
            )
            if price is not None:
                return price

        instance = PriceHistorian()
        price = Price(ZERO)
        for oracle, oracle_instance in instance._oracle_instances:
            oracle_properties = oracle.properties()

            if is_from_fiat_to_fiat and not oracle_properties.has_fiat_to_fiat:
                log.debug(
                    f"Historical price oracle {oracle} can't be used "
                    f"for fiat to fiat. Skipping",
                )
                continue

            if oracle_instance.rate_limited_in_last() is True:
                log.debug(
                    f"Historical price oracle {oracle} can't be used "
                    f"due to rate limits. Skipping",
                )
                continue

            can_query_history = oracle_instance.can_query_history(
                from_asset=from_asset,
                to_asset=to_asset,
                timestam=timestamp,
            )
            if can_query_history is False:
                pass

            try:
                price = oracle_instance.query_historical_price(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    timestamp=timestamp,
                )
            except (PriceQueryUnsupportedAsset, NoPriceForGivenTimestamp, RemoteError) as e:
                log.warning(
                    f'Historical price oracle {oracle} failed to request '
                    f'due to: {str(e)}.',
                    from_asset=from_asset,
                    to_asset=to_asset,
                    timestamp=timestamp,
                )
                continue

            if price != Price(ZERO):
                log.debug(
                    f'Historical price oracle {oracle} got price',
                    price=price,
                    from_asset=from_asset,
                    to_asset=to_asset,
                    timestamp=timestamp,
                )
                return price

            log.error(
                f'Historical price oracle {oracle} failed to request and got zero price',
                price=price,
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )

        raise NoPriceForGivenTimestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            date=timestamp_to_date(timestamp, formatstr='%d/%m/%Y, %H:%M:%S', treat_as_local=True),
        )
