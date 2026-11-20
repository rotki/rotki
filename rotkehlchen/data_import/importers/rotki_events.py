import csv
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    UnsupportedCSVEntry,
    process_rotki_generic_import_csv_fields,
    resolved_csv_locations,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import hash_group_key
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.utils.misc import timestamp_to_date, ts_ms_to_sec

from .constants import ROTKI_EVENT_PREFIX

if TYPE_CHECKING:
    from pathlib import Path

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.fval import FVal
    from rotkehlchen.locations.types import LocationIdentifier
    from rotkehlchen.types import TimestampMS

type LegacyEventKey = tuple[str, int, str, str, str, str, str | None, str | None]

GENERIC_TYPE_TO_HISTORY_EVENT_TYPE_MAPPINGS = {
    'Deposit': (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET),
    'Withdrawal': (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET),
    'Income': (HistoryEventType.RECEIVE, HistoryEventSubType.NONE),
    'Loss': (HistoryEventType.SPEND, HistoryEventSubType.NONE),
    'Spend': (HistoryEventType.SPEND, HistoryEventSubType.NONE),  # synonym of loss
    'Staking': (HistoryEventType.STAKING, HistoryEventSubType.REWARD),
}
SOURCE_ID_COLUMN: Final = 'Source ID'
# Before deterministic identifiers, each imported row got f'{ROTKI_EVENT_PREFIX}_{uuid4().hex}'
LEGACY_GROUP_IDENTIFIER_LENGTH: Final = len(ROTKI_EVENT_PREFIX) + 1 + 32


class RotkiGenericEventsImporter(BaseExchangeImporter):
    """Rotki generic events CSV importer"""

    def __init__(self, db: DBHandler) -> None:
        super().__init__(db=db, name='Rotki generic events')

    def reset(self) -> None:
        super().reset()
        # occurrences of each row identity seen so far in the file being imported
        self._identity_occurrences: defaultdict[str, int] = defaultdict(int)
        self._legacy_events: defaultdict[LegacyEventKey, list[str]] = defaultdict(list)
        self._legacy_events_loaded = False

    def _load_legacy_events(self, write_cursor: DBCursor) -> None:
        """Load old randomly identified generic events once for the current import."""
        groups: defaultdict[str, list[tuple[str, int, str, str, str, str]]] = defaultdict(list)
        for row in write_cursor.execute(
            'SELECT group_identifier, location, timestamp, asset, amount, type, subtype '
            'FROM history_events WHERE group_identifier LIKE ? ESCAPE ? '
            'AND length(group_identifier)=?',
            (f'{ROTKI_EVENT_PREFIX}\\_%', '\\', LEGACY_GROUP_IDENTIFIER_LENGTH),
        ):
            groups[row[0]].append(row[1:])

        serialized_fee_subtype = HistoryEventSubType.FEE.serialize()
        for group_identifier, events in groups.items():
            fee_event = next(
                (event for event in events if event[5] == serialized_fee_subtype),
                None,
            )
            if (main_event := next(
                (event for event in events if event[5] != serialized_fee_subtype),
                None,
            )) is None:
                continue

            self._legacy_events[*main_event, *(
                (fee_event[2], fee_event[3]) if fee_event is not None else (None, None)
            )].append(group_identifier)

        self._legacy_events_loaded = True

    def _migrate_matching_legacy_event(
            self,
            write_cursor: DBCursor,
            identifier: str,
            location: LocationIdentifier,
            timestamp: TimestampMS,
            asset: Asset,
            amount: FVal,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            fee: FVal | None,
            fee_currency: Asset | None,
    ) -> bool:
        """Migrate a matching randomly identified event imported by an older rotki version.

        Those got a random group identifier, so they can only be matched by their attributes.
        Moving the whole group to the deterministic identifier ensures it can only match one row
        across all imports. Fee attributes distinguish otherwise identical legacy events.
        """
        if self._legacy_events_loaded is False:
            self._load_legacy_events(write_cursor)

        has_fee = fee is not None and fee != ZERO
        key: LegacyEventKey = (
            location,
            timestamp,
            asset.identifier,
            str(amount),
            event_type.serialize(),
            event_subtype.serialize(),
            fee_currency.identifier if has_fee and fee_currency is not None else None,
            str(fee) if has_fee else None,
        )
        if len(legacy_identifiers := self._legacy_events[key]) == 0:
            return False

        write_cursor.execute(
            'UPDATE history_events SET group_identifier=? WHERE group_identifier=?',
            (identifier, legacy_identifiers.pop()),
        )
        return True

    def _consume_rotki_event(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            locations: dict[str, LocationIdentifier],
            row_index: int,
    ) -> bool:
        """Consume rotki generic events import CSV file.
        Returns False if the row was skipped as already imported and True otherwise.

        The group identifier is deterministic so that re-importing a file, or a file with
        overlapping history, does not create duplicates. It is derived from the optional
        source id column if given, and otherwise from the row's values plus the number
        of identical rows preceding it in the file, so that legitimately identical rows
        (e.g. identical fills in the same second) are all kept.

        May raise:
        - UnsupportedCSVEntry if an unknown type is encountered.
        - DeserializationError
        - UnknownAsset
        - KeyError
        """
        try:
            event_type, event_subtype = GENERIC_TYPE_TO_HISTORY_EVENT_TYPE_MAPPINGS[csv_row['Type']]  # noqa: E501
        except KeyError as e:
            raise UnsupportedCSVEntry(f'Unsupported entry {csv_row["Type"]}. Data: {csv_row}') from e  # noqa: E501
        asset, fee, fee_currency, location, timestamp = process_rotki_generic_import_csv_fields(csv_row, 'Currency', locations)  # noqa: E501
        amount = deserialize_fval(csv_row['Amount'])
        if (source_id := (csv_row.get(SOURCE_ID_COLUMN) or '').strip()) != '':
            identity = hash_group_key({'location': str(location), 'source_id': source_id})
        else:
            identity = hash_group_key({
                'type': event_type.serialize(),
                'subtype': event_subtype.serialize(),
                'location': str(location),
                'timestamp': timestamp,
                'asset': asset.identifier,
                'amount': str(amount),
                'fee': str(fee) if fee is not None and fee != ZERO else None,
                'fee_currency': (
                    fee_currency.identifier
                    if fee is not None and fee != ZERO and fee_currency is not None else None
                ),
            })
        occurrence = self._identity_occurrences[identity]
        self._identity_occurrences[identity] += 1
        identifier = f'{ROTKI_EVENT_PREFIX}_{hash_group_key({"identity": identity, "occurrence": occurrence})}'  # noqa: E501
        if (
            self.group_already_imported(write_cursor, identifier) or
            self._migrate_matching_legacy_event(
                write_cursor=write_cursor,
                identifier=identifier,
                location=location,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                event_type=event_type,
                event_subtype=event_subtype,
                fee=fee,
                fee_currency=fee_currency,
            )
        ):
            self.append_msg(
                row_index=row_index,
                msg=(
                    f'Skipped already imported {event_type.serialize()}/{event_subtype.serialize()} '  # noqa: E501
                    f'of {amount} {asset.symbol_or_name()} at {timestamp_to_date(ts_ms_to_sec(timestamp), "%Y/%m/%d %H:%M:%S")}'  # noqa: E501
                ),
                is_error=False,
            )
            return False

        events: list[HistoryBaseEntry] = [HistoryEvent(
            group_identifier=identifier,
            sequence_index=0,
            timestamp=timestamp,
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            notes=csv_row['Description'],
        )]
        if fee and fee != ZERO:
            events.append(HistoryEvent(
                group_identifier=identifier,
                sequence_index=1,
                timestamp=timestamp,
                location=location,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=fee_currency,  # type: ignore[arg-type]
                amount=fee,
                notes=csv_row['Description'],
            ))
        self.add_history_events(write_cursor, events)  # event assets are always resolved here
        return True

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """`location_mappings` maps location values of the file to locations.

        May raise:
        - InputError if one of the rows is malformed
        - UnresolvedLocationsError if a location value is neither known nor mapped
        """
        locations = resolved_csv_locations(self.db, filepath, kwargs.get('location_mappings'))
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    if self._consume_rotki_event(write_cursor, row, locations, row_index=index):
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
