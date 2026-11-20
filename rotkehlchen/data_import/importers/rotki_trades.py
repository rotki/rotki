import csv
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    process_rotki_generic_import_csv_fields,
    resolved_csv_locations,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.history.events.utils import create_group_identifier_from_swap, hash_group_key
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import AssetAmount
from rotkehlchen.utils.misc import timestamp_to_date, ts_ms_to_sec

if TYPE_CHECKING:
    from pathlib import Path

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.fval import FVal
    from rotkehlchen.locations.types import LocationIdentifier


class RotkiGenericTradesImporter(BaseExchangeImporter):
    """Rotki generic trades CSV importer"""

    def __init__(self, db: DBHandler) -> None:
        super().__init__(db=db, name='Rotki generic trades')

    def reset(self) -> None:
        super().reset()
        # occurrences of each trade identity seen so far in the file being imported
        self._identity_occurrences: defaultdict[str, int] = defaultdict(int)
        self._base_identifiers_used: set[str] = set()

    @staticmethod
    def _group_fee_matches(
            write_cursor: DBCursor,
            group_identifier: str,
            fee: FVal | None,
            fee_currency: Asset | None,
    ) -> bool:
        """Check whether an existing swap group has the row's normalized fee."""
        fee_row = write_cursor.execute(
            'SELECT asset, amount FROM history_events WHERE group_identifier=? AND subtype=?',
            (group_identifier, HistoryEventSubType.FEE.serialize()),
        ).fetchone()
        if fee is None or fee == ZERO:
            return fee_row is None

        return fee_currency is not None and fee_row == (fee_currency.identifier, str(fee))

    def _consume_rotki_trades(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            locations: dict[str, LocationIdentifier],
            row_index: int,
    ) -> bool:
        """Consume rotki generic trades import CSV file.
        Returns False if the row was skipped as already imported and True otherwise.
        May raise:
        - DeserializationError
        - UnknownAsset
        - KeyError
        """
        spend_amount = deserialize_fval(csv_row['Spend Amount'])
        receive_amount = deserialize_fval(csv_row['Receive Amount'])
        spend_asset, fee, fee_currency, location, timestamp = process_rotki_generic_import_csv_fields(csv_row, 'Spend Currency', locations)  # noqa: E501
        receive_asset = symbol_to_asset_or_token(csv_row['Receive Currency'])
        base_identifier = create_group_identifier_from_swap(
            location=location,
            timestamp=timestamp,
            spend=(spend := AssetAmount(asset=spend_asset, amount=spend_amount)),
            receive=(receive := AssetAmount(asset=receive_asset, amount=receive_amount)),
        )
        has_fee = fee is not None and fee != ZERO
        identity = hash_group_key({
            'swap': base_identifier,
            'fee': str(fee) if has_fee else None,
            'fee_currency': (
                fee_currency.identifier if has_fee and fee_currency is not None else None
            ),
        })
        occurrence = self._identity_occurrences[identity]
        self._identity_occurrences[identity] += 1
        occurrence_identifier = hash_group_key({
            'identity': identity,
            'occurrence': occurrence,
        })
        if self.group_already_imported(write_cursor, occurrence_identifier):
            already_imported = True
            group_identifier = occurrence_identifier
        elif (
            base_identifier not in self._base_identifiers_used and
            self.group_already_imported(write_cursor, base_identifier) and
            self._group_fee_matches(write_cursor, base_identifier, fee, fee_currency)
        ):
            # Older imports used the fee-less base identifier. Keep matching it when the fee
            # agrees, even if a full-history export reordered otherwise identical trades. A base
            # group can satisfy only one occurrence in an import, just like an occurrence group.
            already_imported = True
            group_identifier = base_identifier
            self._base_identifiers_used.add(base_identifier)
        elif (
            base_identifier not in self._base_identifiers_used and
            not self.group_already_imported(write_cursor, base_identifier)
        ):
            # The first new trade keeps the old identifier for backwards compatibility.
            already_imported = False
            group_identifier = base_identifier
            self._base_identifiers_used.add(base_identifier)
        else:
            already_imported = False
            group_identifier = occurrence_identifier

        if already_imported:
            self.append_msg(
                row_index=row_index,
                msg=(
                    f'Skipped already imported trade of {spend_amount} {spend_asset.symbol_or_name()} '  # noqa: E501
                    f'for {receive_amount} {receive_asset.symbol_or_name()} at {timestamp_to_date(ts_ms_to_sec(timestamp), "%Y/%m/%d %H:%M:%S")}'  # noqa: E501
                ),
                is_error=False,
            )
            return False

        self.add_history_events(
            write_cursor=write_cursor,
            history_events=create_swap_events(
                timestamp=timestamp,
                location=location,
                spend=spend,
                receive=receive,
                spend_notes=csv_row['Description'],
                fee=AssetAmount(asset=fee_currency, amount=fee) if fee_currency is not None and fee is not None else None,  # noqa: E501
                group_identifier=group_identifier,
            ),
        )
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
                    if self._consume_rotki_trades(write_cursor, row, locations, row_index=index):
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
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
