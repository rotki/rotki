import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.globaldb.manual_price_oracle import ManualPriceOracle
from rotkehlchen.errors import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_date

from .typing import HistoricalPriceOracle, HistoricalPriceOracleInstance

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures import Balance
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
            f'Could not query usd price for {str(asset)} and time {time} '
            f'when processing {location}. Using zero price',
        )
        usd_price = Price(ZERO)

    return usd_price


def get_balance_asset_rate_at_time_zero_if_error(
        balance: 'Balance',
        asset: Asset,
        timestamp: Timestamp,
        location_hint: str,
        msg_aggregator: MessagesAggregator,
) -> FVal:
    """How many of asset, 1 unit of balance is worth at the given timestamp

    If an error occurs at query we return an asset rate of zero
    """
    usd_rate = balance.usd_rate
    price = query_usd_price_zero_if_error(
        asset=asset,
        time=timestamp,
        location=location_hint,
        msg_aggregator=msg_aggregator,
    )
    if price == ZERO:
        return ZERO
    return usd_rate / price


class PriceHistorian():
    __instance: Optional['PriceHistorian'] = None
    _cryptocompare: 'Cryptocompare'
    _coingecko: 'Coingecko'
    _manual: ManualPriceOracle
    _oracles: Optional[List[HistoricalPriceOracle]] = None
    _oracle_instances: Optional[List[HistoricalPriceOracleInstance]] = None

    def __new__(
            cls,
            data_directory: Path = None,
            cryptocompare: 'Cryptocompare' = None,
            coingecko: 'Coingecko' = None,
    ) -> 'PriceHistorian':
        if PriceHistorian.__instance is not None:
            return PriceHistorian.__instance

        assert data_directory, 'arguments should be given at the first instantiation'
        assert cryptocompare, 'arguments should be given at the first instantiation'
        assert coingecko, 'arguments should be given at the first instantiation'

        PriceHistorian.__instance = object.__new__(cls)
        PriceHistorian._cryptocompare = cryptocompare
        PriceHistorian._coingecko = coingecko
        PriceHistorian._manual = ManualPriceOracle()

        return PriceHistorian.__instance

    @staticmethod
    def set_oracles_order(oracles: List[HistoricalPriceOracle]) -> None:
        assert len(oracles) != 0 and len(oracles) == len(set(oracles)), (
            'Oracles can\'t be empty or have repeated items'
        )
        instance = PriceHistorian()
        instance._oracles = oracles
        instance._oracle_instances = [getattr(instance, f'_{str(oracle)}') for oracle in oracles]

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

        # Querying historical forex data is attempted first via the external apis
        # and then via any price oracle that has fiat to fiat.
        if from_asset.is_fiat() and to_asset.is_fiat():
            price = Inquirer().query_historical_fiat_exchange_rates(
                from_fiat_currency=from_asset,
                to_fiat_currency=to_asset,
                timestamp=timestamp,
            )
            if price is not None:
                return price
            # else cryptocompare also has historical fiat to fiat data

        instance = PriceHistorian()
        oracles = instance._oracles
        oracle_instances = instance._oracle_instances
        assert isinstance(oracles, list) and isinstance(oracle_instances, list), (
            'PriceHistorian should never be called before the setting the oracles'
        )
        for oracle, oracle_instance in zip(oracles, oracle_instances):
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

        raise NoPriceForGivenTimestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            date=timestamp_to_date(timestamp, formatstr='%d/%m/%Y, %H:%M:%S', treat_as_local=True),
        )
