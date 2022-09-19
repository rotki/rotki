import logging
import sqlite3
from typing import TYPE_CHECKING, Iterable, List

from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import BinancePair
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from .handler import GlobalDBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GlobalDBBinance:

    def __init__(self, globaldb: 'GlobalDBHandler') -> None:
        self.db = globaldb

    def save_all_binance_pairs(
            self,
            new_pairs: Iterable[BinancePair],
            location: Location,
    ) -> None:
        """Saves all possible binance pairs into the GlobalDB.
        NB: This is not the user-selected binance pairs. This is just a cache.

        May raise:
        - InputError if there is a DB insertion failure
        """
        query = 'INSERT OR IGNORE INTO binance_pairs(pair, base_asset, quote_asset, location) VALUES (?, ?, ?, ?)'  # noqa: E501
        cursor = self.db.conn.cursor()
        try:
            cursor.executemany(query, [pair.serialize_for_db() for pair in new_pairs])
            self.db.add_setting_value(name=f'binance_pairs_queried_at_{location}', value=ts_now())
        except sqlite3.IntegrityError as e:
            raise InputError(
                f'Tried to add a binance pair to the database but failed due to {str(e)}',
            ) from e

    def get_all_binance_pairs(self, location: Location) -> List[BinancePair]:
        """Gets all possible binance pairs from the GlobalDB.
        NB: This is not the user-selected binance pairs. This is just a cache.
        """
        cursor = self.db.conn.cursor()
        cursor.execute(
            'SELECT pair, base_asset, quote_asset, location FROM binance_pairs WHERE location=?',
            (location.serialize_for_db(),),
        )
        pairs = []
        for pair in cursor:
            try:
                pairs.append(BinancePair.deserialize_from_db(pair))
            except (DeserializationError, UnsupportedAsset, UnknownAsset) as e:
                log.debug(f'Failed to deserialize binance pair {pair}. {str(e)}')
        return pairs
