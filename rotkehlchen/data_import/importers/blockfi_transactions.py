import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.converters import asset_from_blockfi
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    SkippedCSVEntry,
    UnsupportedCSVEntry,
    hash_csv_row,
)
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BLOCKFI_PREFIX = 'BLF_'


class BlockfiTransactionsImporter(BaseExchangeImporter):
    """Blockfi transactions CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Blockfi transactions')

    def _consume_blockfi_entry(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%Y-%m-%d %H:%M:%S',
    ) -> None:
        """
        Process entry for BlockFi transaction history. Trades for this file are ignored
        and instead should be extracted from the file containing only trades.
        This method can raise:
        - UnsupportedBlockFiEntry
        - UnknownAsset
        - DeserializationError
        """
        if len(csv_row['Confirmed At']) != 0:
            timestamp = deserialize_timestamp_from_date(
                date=csv_row['Confirmed At'],
                formatstr=timestamp_format,
                location='BlockFi',
            )
        else:
            raise SkippedCSVEntry('Entry is unconfirmed.')

        asset = asset_from_blockfi(csv_row['Cryptocurrency'])
        raw_amount = deserialize_fval(csv_row['Amount'])
        abs_amount = abs(raw_amount)
        entry_type = csv_row['Transaction Type']

        if entry_type in {'Deposit', 'Wire Deposit', 'ACH Deposit'}:
            self.add_history_events(write_cursor, [AssetMovement(
                location=Location.BLOCKFI,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=ts_sec_to_ms(timestamp),
                asset=asset,
                amount=abs_amount,
            )])
        elif entry_type in {'Withdrawal', 'Wire Withdrawal', 'ACH Withdrawal'}:
            self.add_history_events(write_cursor, [AssetMovement(
                location=Location.BLOCKFI,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=ts_sec_to_ms(timestamp),
                asset=asset,
                amount=abs_amount,
            )])
        elif entry_type == 'Withdrawal Fee':
            self.add_history_events(write_cursor, [AssetMovement(
                location=Location.BLOCKFI,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=ts_sec_to_ms(timestamp),
                asset=asset,
                amount=abs_amount,
                is_fee=True,
            )])
        elif entry_type in {'Interest Payment', 'Bonus Payment', 'Referral Bonus'}:
            event = HistoryEvent(
                group_identifier=f'{BLOCKFI_PREFIX}{hash_csv_row(csv_row)}',
                sequence_index=0,
                timestamp=ts_sec_to_ms(timestamp),
                location=Location.BLOCKFI,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                amount=abs_amount,
                asset=asset,
                notes=f'{entry_type} from BlockFi',
            )
            self.add_history_events(write_cursor, [event])
        elif entry_type == 'Crypto Transfer':
            self.add_history_events(write_cursor, [AssetMovement(
                location=Location.BLOCKFI,
                event_type=HistoryEventType.WITHDRAWAL if raw_amount < ZERO else HistoryEventType.DEPOSIT,  # noqa: E501
                timestamp=ts_sec_to_ms(timestamp),
                asset=asset,
                amount=abs_amount,
            )])
        elif entry_type == 'Trade':
            raise SkippedCSVEntry('Entry is a trade.')
        else:
            raise UnsupportedCSVEntry(f'Unsupported entry {entry_type}. Data: {csv_row}')

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from
        https://github.com/BittyTax/BittyTax/blob/06794f51223398759852d6853bc7112ffb96129a/bittytax/conv/parsers/blockfi.py#L67
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    self._consume_blockfi_entry(write_cursor, row, **kwargs)
                    self.imported_entries += 1
                except UnknownAsset as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Unknown asset {e.identifier}.',
                        is_error=True,
                    )
                except DeserializationError as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Deserialization error: {e!s}.',
                        is_error=True,
                    )
                except UnsupportedCSVEntry as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=str(e),
                        is_error=True,
                    )
                except SkippedCSVEntry as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=str(e),
                        is_error=False,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
