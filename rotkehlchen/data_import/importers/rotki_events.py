import csv
from pathlib import Path
from typing import Any
from uuid import uuid4

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
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
from rotkehlchen.serialization.deserialize import deserialize_asset_amount

from .constants import ROTKI_EVENT_PREFIX

GENERIC_TYPE_TO_HISTORY_EVENT_TYPE_MAPPINGS = {
    'Deposit': (HistoryEventType.DEPOSIT, HistoryEventSubType.SPEND),
    'Withdrawal': (HistoryEventType.WITHDRAWAL, HistoryEventSubType.RECEIVE),
    'Income': (HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE),
    'Loss': (HistoryEventType.SPEND, HistoryEventSubType.NONE),
    'Staking': (HistoryEventType.STAKING, HistoryEventSubType.REWARD),
}


class RotkiGenericEventsImporter(BaseExchangeImporter):
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
            balance=Balance(
                amount=deserialize_asset_amount(csv_row['Amount']),
                usd_value=ZERO,
            ),
            notes=csv_row['Description'],
        )
        events.append(history_event)
        if fee:
            fee_event = HistoryEvent(
                event_identifier=identifier,
                sequence_index=sequence_index + 1,
                timestamp=timestamp,
                location=location,
                event_type=event_type,
                event_subtype=HistoryEventSubType.FEE,
                asset=fee_currency,  # type: ignore[arg-type]
                balance=Balance(
                    amount=fee,
                    usd_value=ZERO,
                ),
                notes=csv_row['Description'],
            )
            events.append(fee_event)
        self.add_history_events(write_cursor, events)  # event assets are always resolved here

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for idx, row in enumerate(data):
                try:
                    kwargs['sequence_index'] = idx
                    self._consume_rotki_event(write_cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During rotki generic events CSV import, found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during rotki generic events CSV import. '
                        f'{e!s}. Ignoring entry',
                    )
                except UnsupportedCSVEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e

                # if more logic is ever added here,
                # `continue` must be placed at the end of all the exceptions handlers
