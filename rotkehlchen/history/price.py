import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import FilePath, Price, Timestamp
from rotkehlchen.utils.misc import create_timestamp

if TYPE_CHECKING:
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PriceHistorian():
    __instance: Optional['PriceHistorian'] = None
    _historical_data_start: Timestamp
    _cryptocompare: 'Cryptocompare'

    def __new__(
            cls,
            data_directory: FilePath = None,
            history_date_start: str = None,
            cryptocompare: 'Cryptocompare' = None,
    ) -> 'PriceHistorian':
        if PriceHistorian.__instance is not None:
            return PriceHistorian.__instance
        assert data_directory, 'arguments should be given at the first instantiation'
        assert history_date_start, 'arguments should be given at the first instantiation'
        assert cryptocompare, 'arguments should be given at the first instantiation'

        PriceHistorian.__instance = object.__new__(cls)

        # get the start date for historical data
        PriceHistorian._historical_data_start = create_timestamp(
            datestr=history_date_start,
            formatstr="%d/%m/%Y",
        )
        PriceHistorian._cryptocompare = cryptocompare

        return PriceHistorian.__instance

    @staticmethod
    def query_historical_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
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
        - PriceQueryUnknownFromAsset if the from asset is known to miss from cryptocompare
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the external service.
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        log.debug(
            'Querying historical price',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )

        if from_asset == to_asset:
            return Price(FVal('1'))

        if from_asset.is_fiat() and to_asset.is_fiat():
            # if we are querying historical forex data then try something other than cryptocompare
            price = Inquirer().query_historical_fiat_exchange_rates(
                from_fiat_currency=from_asset,
                to_fiat_currency=to_asset,
                timestamp=timestamp,
            )
            if price is not None:
                return price
            # else cryptocompare also has historical fiat to fiat data

        instance = PriceHistorian()
        return instance._cryptocompare.query_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            historical_data_start=instance._historical_data_start,
        )
