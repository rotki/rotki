import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.converters import asset_from_common_identifier
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Xaman CSV exports have no header row. These are the column names
# inferred from the data format:
# sequence_id, direction, tx_type, timestamp, currency, amount, fee, tx_hash, account, dest_tag
XAMAN_FIELDNAMES = (
    'sequence_id',
    'direction',
    'tx_type',
    'timestamp',
    'currency',
    'amount',
    'fee',
    'tx_hash',
    'account',
    'dest_tag',
)


class XamanImporter(BaseExchangeImporter):
    """Xaman (formerly XUMM) XRPL wallet CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Xaman')

    def _consume_xaman_entry(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
    ) -> None:
        """
        Consume a single row from a Xaman CSV export.
        Xaman exports contain XRPL transactions (Payment, OfferCreate, etc.).
        We only handle Payment transactions as receive/send events.

        May raise:
        - UnsupportedCSVEntry
        - DeserializationError
        - UnknownAsset
        """
        tx_type = csv_row.get('tx_type', '')
        if tx_type != 'Payment':
            raise UnsupportedCSVEntry(f'Unsupported Xaman transaction type: {tx_type}')

        direction = csv_row.get('direction', '')
        if direction not in ('received', 'sent'):
            raise UnsupportedCSVEntry(f'Unknown Xaman direction: {direction}')

        timestamp = deserialize_timestamp_from_date(
            date=csv_row['timestamp'],
            formatstr='%Y-%m-%dT%H:%M:%S.%fZ',
            location='Xaman',
        )
        timestamp_ms = ts_sec_to_ms(timestamp)

        currency_str = csv_row.get('currency', 'XRP')
        if currency_str == 'XRP':
            from rotkehlchen.constants.assets import A_XRP
            asset = A_XRP
        else:
            asset = asset_from_common_identifier(currency_str)

        amount = deserialize_fval(
            value=csv_row['amount'],
            name='amount',
            location='Xaman',
        )
        fee_raw = csv_row.get('fee', '0')
        fee = deserialize_fval(
            value=fee_raw if fee_raw != '' else '0',
            name='fee',
            location='Xaman',
        )

        tx_hash = csv_row.get('tx_hash', '')
        notes = f'Xaman XRPL {direction} {amount} {currency_str}'
        if tx_hash:
            notes += f' (tx: {tx_hash[:16]}...)'

        if direction == 'received':
            event_type = HistoryEventType.RECEIVE
            event_subtype = HistoryEventSubType.NONE
        else:  # sent
            event_type = HistoryEventType.SPEND
            event_subtype = HistoryEventSubType.NONE

        event = HistoryEvent(
            event_identifier=f'XAMAN_{tx_hash}',
            sequence_index=0,
            timestamp=timestamp_ms,
            location=Location.EXTERNAL,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            balance=AssetAmount(amount=amount),
            notes=notes,
        )
        self.add_history_events(write_cursor=write_cursor, history_events=[event])

        # Add fee as separate event if non-zero (only sender pays fee on XRPL)
        if direction == 'sent' and fee > ZERO:
            from rotkehlchen.constants.assets import A_XRP
            fee_event = HistoryEvent(
                event_identifier=f'XAMAN_{tx_hash}_fee',
                sequence_index=1,
                timestamp=timestamp_ms,
                location=Location.EXTERNAL,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_XRP,  # XRPL fees are always in XRP
                balance=AssetAmount(amount=fee),
                notes='Xaman XRPL transaction fee',
            )
            self.add_history_events(write_cursor=write_cursor, history_events=[fee_event])

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Import CSV data from Xaman (XRPL wallet, formerly XUMM).
        Xaman CSVs have no header row, so we provide explicit fieldnames.

        May raise:
        - InputError if a row is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(
                csv.DictReader(csvfile, fieldnames=XAMAN_FIELDNAMES),
                start=1,
            ):
                try:
                    self.total_entries += 1
                    self._consume_xaman_entry(write_cursor, row)
                    self.imported_entries += 1
                except UnsupportedCSVEntry as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=str(e),
                        is_error=False,
                    )
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
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
