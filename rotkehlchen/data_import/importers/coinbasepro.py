import csv
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from rotkehlchen.assets.converters import asset_from_coinbasepro
from rotkehlchen.data_import.importers.constants import COINBASEPRO_EVENT_PREFIX
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


class CoinbaseProImporter(BaseExchangeImporter):
    """GDAX/Coinbase Pro CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Coinbase Pro')

    def _consume_deposit_withdrawal(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%Y-%m-%dT%H:%M:%S.%f',
    ) -> None:
        """Process a deposit or withdrawal row.
        May raise:
        - UnknownAsset
        - DeserializationError
        - KeyError
        """
        timestamp = ts_sec_to_ms(deserialize_timestamp_from_date(
            date=csv_row['Timestamp'],
            formatstr=timestamp_format,
            location='Coinbase Pro',
        ))
        asset = asset_from_coinbasepro(csv_row['Amount/balance unit'])

        self.add_history_events(
            write_cursor=write_cursor,
            history_events=[AssetMovement(
                group_identifier=f'{COINBASEPRO_EVENT_PREFIX}_{uuid4().hex}',
                event_subtype=(
                    HistoryEventSubType.RECEIVE
                    if csv_row['Type'] == 'deposit'
                    else HistoryEventSubType.SPEND
                ),
                timestamp=timestamp,
                location=Location.COINBASEPRO,
                asset=asset,
                amount=abs(deserialize_fval(csv_row['Amount'])),
            )],
        )

    def _consume_trade_group(
            self,
            write_cursor: DBCursor,
            rows: list[dict[str, Any]],
            timestamp_format: str = '%Y-%m-%dT%H:%M:%S.%f',
    ) -> None:
        """Process a group of match/fee rows sharing the same Trade id.

        Each trade id group has exactly:
        - One match row with positive amount (receive side)
        - One match row with negative amount (spend side)
        - One fee row with negative amount

        May raise:
        - UnknownAsset
        - DeserializationError
        - KeyError
        - ValueError
        """
        receive_row: dict[str, Any] | None = None
        spend_row: dict[str, Any] | None = None
        fee_row: dict[str, Any] | None = None

        for row in rows:
            if row['Type'] == 'fee':
                fee_row = row
            elif row['Type'] == 'match':
                raw = deserialize_fval(row['Amount'])
                if raw > 0:
                    receive_row = row
                else:
                    spend_row = row

        if receive_row is None or spend_row is None:
            raise DeserializationError(
                f'Trade id {rows[0].get("Trade id")} missing match rows',
            )

        timestamp = ts_sec_to_ms(deserialize_timestamp_from_date(
            date=receive_row['Timestamp'],
            formatstr=timestamp_format,
            location='Coinbase Pro',
        ))

        receive_amount = deserialize_fval(receive_row['Amount'])
        receive_asset = asset_from_coinbasepro(receive_row['Amount/balance unit'])
        spend_amount = abs(deserialize_fval(spend_row['Amount']))
        spend_asset = asset_from_coinbasepro(spend_row['Amount/balance unit'])

        fee: AssetAmount | None = None
        if fee_row is not None:
            fee = AssetAmount(
                asset=asset_from_coinbasepro(fee_row['Amount/balance unit']),
                amount=abs(deserialize_fval(fee_row['Amount'])),
            )

        events: list[HistoryBaseEntry] = list(create_swap_events(
            timestamp=timestamp,
            location=Location.COINBASEPRO,
            spend=AssetAmount(asset=spend_asset, amount=spend_amount),
            receive=AssetAmount(asset=receive_asset, amount=receive_amount),
            group_identifier=f'{COINBASEPRO_EVENT_PREFIX}_{uuid4().hex}',
            fee=fee,
        ))
        self.add_history_events(write_cursor=write_cursor, history_events=events)

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """Import CSV data from a GDAX/Coinbase Pro account statement."""
        # First pass: collect all rows, grouping trade-related rows by Trade id
        trade_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        non_trade_rows: list[tuple[int, dict[str, Any]]] = []

        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                # Skip empty rows (the GDAX CSV often has trailing empty rows)
                if not row.get('Type'):
                    continue

                row_type = row['Type']
                if row_type in {'match', 'fee'}:
                    trade_id = row.get('Trade id', '')
                    if not trade_id:
                        self.send_message(
                            row_index=index, csv_row=row,
                            msg='Match/fee row without Trade id.', is_error=True,
                        )
                        continue
                    trade_groups[trade_id].append(row)
                elif row_type in {'deposit', 'withdrawal'}:
                    non_trade_rows.append((index, row))
                else:
                    self.send_message(
                        row_index=index, csv_row=row,
                        msg=f'Unknown row type {row_type}.', is_error=True,
                    )

        # Process deposits/withdrawals
        for index, row in non_trade_rows:
            try:
                self.total_entries += 1
                self._consume_deposit_withdrawal(write_cursor, row, **kwargs)
                self.imported_entries += 1
            except UnknownAsset as e:
                self.send_message(
                    row_index=index, csv_row=row,
                    msg=f'Unknown asset {e.identifier}.', is_error=True,
                )
            except DeserializationError as e:
                self.send_message(
                    row_index=index, csv_row=row,
                    msg=f'Deserialization error: {e!s}.', is_error=True,
                )
            except KeyError as e:
                raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e

        # Process trade groups
        for trade_id, rows in trade_groups.items():
            try:
                self.total_entries += 1
                self._consume_trade_group(write_cursor, rows, **kwargs)
                self.imported_entries += 1
            except UnknownAsset as e:
                self.send_message(
                    row_index=0, csv_row=rows[0],
                    msg=f'Unknown asset {e.identifier} in trade {trade_id}.',
                    is_error=True,
                )
            except (DeserializationError, ValueError) as e:
                self.send_message(
                    row_index=0, csv_row=rows[0],
                    msg=f'Error processing trade {trade_id}: {e!s}.',
                    is_error=True,
                )
            except KeyError as e:
                raise InputError(
                    f'Could not find key {e!s} in trade group {trade_id}',
                ) from e
