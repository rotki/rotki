import logging
from typing import Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import NoPriceForGivenTimestamp
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.typing import HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Price, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ManualPriceOracle:

    def can_query_history(  # pylint: disable=no-self-use
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return True

    @classmethod
    def query_historical_price(
        cls,
        from_asset: Asset,
        to_asset: Asset,
        timestamp: Timestamp,
    ) -> Price:
        price_entry = GlobalDBHandler().get_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            max_seconds_distance=3600,
            source=HistoricalPriceOracle.MANUAL,
        )
        if price_entry and price_entry.price != Price(ZERO):
            log.debug('Got historical manual price', from_asset=from_asset, to_asset=to_asset, timestamp=timestamp)  # noqa: E501
            return price_entry.price

        log.debug(
            f'Could not find manual historical price from {from_asset} to '
            f'{to_asset} at timestamp {timestamp} .',
        )
        raise NoPriceForGivenTimestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            date=timestamp_to_date(
                timestamp,
                formatstr='%d/%m/%Y, %H:%M:%S',
                treat_as_local=True,
            ),
        )
