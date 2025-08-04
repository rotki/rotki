import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING

import rsqlite

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
        with self.db.conn.write_ctx() as write_cursor:
            try:
                write_cursor.executemany(query, [pair.serialize_for_db() for pair in new_pairs])
            except rsqlite.IntegrityError as e:
                raise InputError(
                    f'Tried to add a binance pair to the database but failed due to {e!s}',
                ) from e

        self.db.add_setting_value(name=f'binance_pairs_queried_at_{location}', value=ts_now())

    def get_all_binance_pairs(self, location: Location) -> list[BinancePair]:
        """Gets all possible binance pairs from the GlobalDB.
        NB: This is not the user-selected binance pairs. This is just a cache.
        """
        pairs = []
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT pair, base_asset, quote_asset, location FROM binance_pairs WHERE location=?',  # noqa: E501
                (location.serialize_for_db(),),
            )
            for pair in cursor:
                try:
                    pairs.append(BinancePair.deserialize_from_db(pair))
                except (DeserializationError, UnsupportedAsset, UnknownAsset) as e:
                    log.debug(f'Failed to deserialize binance pair {pair}. {e!s}')

        return pairs
