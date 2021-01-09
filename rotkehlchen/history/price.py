import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import NoPriceForGivenTimestamp, RemoteError, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_date
if TYPE_CHECKING:
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.externalapis.coingecko import Coingecko

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
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
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
        price = None
        if Inquirer()._cryptocompare.rate_limited_in_last() is False:
            try:
                price = instance._cryptocompare.query_historical_price(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    timestamp=timestamp,
                )
            except (PriceQueryUnsupportedAsset, NoPriceForGivenTimestamp, RemoteError):
                # then use coingecko
                pass

        if price and price != Price(ZERO):
            return price

        try:
            price = instance._coingecko.historical_price(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )
            if price != Price(ZERO):
                return price
        except RemoteError:
            pass

        # nothing found in any price oracle
        raise NoPriceForGivenTimestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            date=timestamp_to_date(timestamp, formatstr='%d/%m/%Y, %H:%M:%S'),
        )
