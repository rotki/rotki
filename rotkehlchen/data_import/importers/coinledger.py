import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.converters import LOCATION_TO_ASSET_MAPPING
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.data_import.importers.constants import COINLEDGER_EVENT_PREFIX
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    UnsupportedCSVEntry,
    maybe_set_transaction_extra_data,
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
    deserialize_fval_force_positive,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def platform_row_to_location(entry: str) -> Location:
    """Takes the Platform value from CoinLedger and returns a location."""
    try:
        return Location.deserialize(entry)
    except DeserializationError:
        if entry == 'Binance Smart Chain':
            return Location.BINANCE_SC

    log.warning(f'Coinledger Location "{entry}" unrecognized and imported as external')
    return Location.EXTERNAL


class CoinledgerImporter(BaseExchangeImporter):
    """CoinLedger CSV importer."""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='CoinLedger')
        self._group_sequence_index: dict[str, int] = {}

    def reset(self) -> None:
        super().reset()
        self._group_sequence_index = {}

    def _consume_coinledger_entry(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%Y-%m-%dT%H:%M:%S.%f',
    ) -> None:
        """Consumes a CoinLedger CSV row and adds it into the database.

        Can raise:
            - DeserializationError if expected values are malformed
            - UnsupportedCSVEntry if the row is unsupported
            - KeyError if an expected CSV key is missing
            - UnknownAsset if one of the assets in the row is not supported
        """
        timestamp = ts_sec_to_ms(deserialize_timestamp_from_date(
            date=csv_row['Timestamp (UTC)'],
            formatstr=timestamp_format,
            location='CoinLedger',
        ))
        location = platform_row_to_location(csv_row['Platform'])
        asset_resolver = LOCATION_TO_ASSET_MAPPING.get(location, symbol_to_asset_or_token)
        asset = asset_resolver(csv_row['Asset'])
        amount = deserialize_fval_force_positive(csv_row['Amount'])
        row_type = csv_row['Type']
        record_type = csv_row['Record Type']
        internal_id = csv_row['Internal Id']
        transaction_id = csv_row['Blockchain Id'] or csv_row['Platform Id'] or None
        extra_data = maybe_set_transaction_extra_data(address=None, transaction_id=transaction_id)
        notes = (
            f'{row_type} ({record_type}) from CoinLedger'
            if csv_row['Description'] == ''
            else f'{row_type} ({record_type}) from CoinLedger: {csv_row["Description"]}'
        )

        if row_type in {'Deposit', 'Withdrawal'} and record_type in {'Credit', 'Debit'}:
            movement_subtype: Literal[
                HistoryEventSubType.RECEIVE,
                HistoryEventSubType.SPEND,
            ]
            if record_type == 'Credit':
                movement_subtype = HistoryEventSubType.RECEIVE
            else:
                movement_subtype = HistoryEventSubType.SPEND
            self.add_history_events(write_cursor, [AssetMovement(
                timestamp=timestamp,
                location=location,
                event_subtype=movement_subtype,
                asset=asset,
                amount=amount,
                unique_id=internal_id,
                extra_data=extra_data,
                location_label=csv_row['Account Name'] or None,
                notes=notes,
            )])
            return

        if record_type == 'Credit':
            event_type = HistoryEventType.RECEIVE
            event_subtype = HistoryEventSubType.NONE
        elif record_type in {'Debit', 'Platform Fee'}:
            event_type = HistoryEventType.SPEND
            event_subtype = (
                HistoryEventSubType.FEE
                if record_type == 'Platform Fee'
                else HistoryEventSubType.NONE
            )
        elif record_type == 'Margin Gain':
            event_type = HistoryEventType.RECEIVE
            event_subtype = HistoryEventSubType.NONE
        else:
            raise UnsupportedCSVEntry(
                f'Unknown record type "{record_type}" encountered during coinledger data import. '
                f'Ignoring entry',
            )

        group_identifier = f'{COINLEDGER_EVENT_PREFIX}_{internal_id}'
        sequence_index = self._group_sequence_index.get(group_identifier, 0)
        self._group_sequence_index[group_identifier] = sequence_index + 1
        history_extra_data = None if extra_data is None else dict(extra_data)
        self.add_history_events(write_cursor, [HistoryEvent(
            group_identifier=group_identifier,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            extra_data=history_extra_data,
            location_label=csv_row['Account Name'] or None,
            notes=notes,
        )])

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """Import transactions from CoinLedger CSV exports."""
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile, delimiter=',', quotechar='"')
            for index, row in enumerate(data, start=1):
                self.total_entries += 1
                try:
                    self._consume_coinledger_entry(write_cursor, row, **kwargs)
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
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
