import csv
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_timestamp
from rotkehlchen.types import Fee, Location, TimestampMS

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
            cursor: DBCursor,
            csv_row: Dict[str, Any],
            sequence_index: int,
    ) -> None:
        """Consume rotki generic events import CSV file.
        May raise:
        - UnsupportedCSVEntry if an unknown type is encountered.
        - DeserializationError
        - UnknownAsset
        - KeyError
        """
        identifier = f'rotki_events_{uuid4().hex}'
        try:
            event_type, event_subtype = GENERIC_TYPE_TO_HISTORY_EVENT_TYPE_MAPPINGS[csv_row['Type']]  # noqa: E501
        except KeyError as e:
            raise UnsupportedCSVEntry(f'Unsupported entry {csv_row["Type"]}. Data: {csv_row}') from e  # noqa: E501
        events: List[HistoryBaseEntry] = []
        location = Location.deserialize(csv_row['Location'])
        timestamp = TimestampMS(deserialize_timestamp(csv_row['Timestamp']))
        fee = Fee(deserialize_asset_amount(csv_row['Fee'])) if csv_row['Fee'] else Fee(ZERO)  # noqa: E501
        fee_currency = (
            symbol_to_asset_or_token(csv_row['Fee Currency'])
            if csv_row['Fee Currency'] and fee is not None else None
        )
        history_event = HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(identifier),
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=symbol_to_asset_or_token(csv_row['Currency']),
            balance=Balance(
                amount=deserialize_asset_amount(csv_row['Amount']),
                usd_value=ZERO,
            ),
            notes=csv_row['Description'],
        )
        events.append(history_event)
        if fee != ZERO and fee_currency is not None:
            fee_event = HistoryBaseEntry(
                event_identifier=HistoryBaseEntry.deserialize_event_identifier(identifier),
                sequence_index=sequence_index + 1,
                timestamp=timestamp,
                location=location,
                event_type=event_type,
                event_subtype=HistoryEventSubType.FEE,
                asset=fee_currency,
                balance=Balance(
                    amount=fee,
                    usd_value=ZERO,
                ),
                notes=csv_row['Description'],
            )
            events.append(fee_event)
        self.add_history_events(cursor, events)  # event assets are always resolved here

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for idx, row in enumerate(data):
                try:
                    kwargs['sequence_index'] = idx
                    self._consume_rotki_event(cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During rotki generic events CSV import, found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during rotki generic events CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except UnsupportedCSVEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                    continue
                except KeyError as e:
                    raise InputError(f'Could not find key {str(e)} in csv row {str(row)}') from e
