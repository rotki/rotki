import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    UnsupportedCSVEntry,
    process_rotki_generic_import_csv_fields,
)
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_fval

from .constants import ROTKI_EVENT_PREFIX

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

GENERIC_TYPE_TO_HISTORY_EVENT_TYPE_MAPPINGS = {
    'Deposit': (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET),
    'Withdrawal': (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET),
    'Income': (HistoryEventType.RECEIVE, HistoryEventSubType.NONE),
    'Loss': (HistoryEventType.SPEND, HistoryEventSubType.NONE),
    'Spend': (HistoryEventType.SPEND, HistoryEventSubType.NONE),  # synonym of loss
    'Staking': (HistoryEventType.STAKING, HistoryEventSubType.REWARD),
}


class RotkiGenericEventsImporter(BaseExchangeImporter):
    """Rotki generic events CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Rotki generic events')

    def _consume_rotki_event(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            sequence_index: int,
    ) -> None:
        """Consume rotki generic events import CSV file.
        May raise:
        - UnsupportedCSVEntry if an unknown type is encountered.
        - DeserializationError
        - UnknownAsset
        - KeyError
        """
        identifier = f'{ROTKI_EVENT_PREFIX}_{uuid4().hex}'
        try:
            event_type, event_subtype = GENERIC_TYPE_TO_HISTORY_EVENT_TYPE_MAPPINGS[csv_row['Type']]  # noqa: E501
        except KeyError as e:
            raise UnsupportedCSVEntry(f'Unsupported entry {csv_row["Type"]}. Data: {csv_row}') from e  # noqa: E501
        events: list[HistoryBaseEntry] = []
        asset, fee, fee_currency, location, timestamp = process_rotki_generic_import_csv_fields(csv_row, 'Currency')  # noqa: E501
        history_event = HistoryEvent(
            event_identifier=identifier,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=deserialize_fval(csv_row['Amount']),
            notes=csv_row['Description'],
        )
        events.append(history_event)
        if fee and fee != ZERO:
            fee_event = HistoryEvent(
                event_identifier=identifier,
                sequence_index=sequence_index + 1,
                timestamp=timestamp,
                location=location,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=fee_currency,  # type: ignore[arg-type]
                amount=fee,
                notes=csv_row['Description'],
            )
            events.append(fee_event)
        self.add_history_events(write_cursor, events)  # event assets are always resolved here

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    kwargs['sequence_index'] = index - 1
                    self._consume_rotki_event(write_cursor, row, **kwargs)
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
