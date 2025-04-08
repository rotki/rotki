import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.converters import asset_from_uphold
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import BaseExchangeImporter, SkippedCSVEntry, hash_csv_row
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


UPHOLD_PREFIX = 'UPH_'


class UpholdTransactionsImporter(BaseExchangeImporter):
    """Uphold CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Uphold')

    def _consume_uphold_transaction(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%a %b %d %Y %H:%M:%S %Z%z',
    ) -> None:
        """
        Consume the file containing both trades and transactions from uphold.
        This method can raise:
        - UnknownAsset
        - DeserializationError
        - KeyError
        """
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr=timestamp_format,
            location='uphold',
        )
        destination = csv_row['Destination']
        destination_asset = asset_from_uphold(csv_row['Destination Currency'])
        destination_amount = deserialize_asset_amount(csv_row['Destination Amount'])
        origin = csv_row['Origin']
        origin_asset = asset_from_uphold(csv_row['Origin Currency'])
        origin_amount = deserialize_asset_amount(csv_row['Origin Amount'])
        if csv_row['Fee Amount'] == '':
            fee = FVal(ZERO)
        else:
            fee = deserialize_fee(csv_row['Fee Amount'])
        fee_asset = asset_from_uphold(csv_row['Fee Currency'] or csv_row['Origin Currency'])
        transaction_type = csv_row['Type']
        notes = f"""
Activity from uphold with uphold transaction id:
 {csv_row['Id']}, origin: {csv_row['Origin']},
 and destination: {csv_row['Destination']}.
  Type: {csv_row['Type']}.
  Status: {csv_row['Status']}.
"""
        if origin == destination == 'uphold':  # On exchange Transfers / Trades
            if origin_asset == destination_asset and origin_amount == destination_amount:
                if transaction_type == 'in':
                    event_type = HistoryEventType.RECEIVE
                elif transaction_type == 'out':
                    event_type = HistoryEventType.SPEND
                else:
                    raise SkippedCSVEntry(f'Uncaught transaction type: {transaction_type}.')
                event = HistoryEvent(
                    event_identifier=f'{UPHOLD_PREFIX}{hash_csv_row(csv_row)}',
                    sequence_index=0,
                    timestamp=ts_sec_to_ms(timestamp),
                    location=Location.UPHOLD,
                    event_type=event_type,
                    event_subtype=HistoryEventSubType.NONE,
                    amount=destination_amount,
                    asset=destination_asset,
                    notes=notes,
                )
                self.add_history_events(write_cursor, [event])
            else:  # Assets or amounts differ (Trades)
                # in uphold UI the exchanged amount includes the fee.
                if fee_asset == destination_asset:
                    destination_amount = AssetAmount(destination_amount + fee)
                if destination_amount > 0:
                    self.add_history_events(
                        write_cursor=write_cursor,
                        history_events=create_swap_events(
                            timestamp=ts_sec_to_ms(timestamp),
                            location=Location.UPHOLD,
                            spend_asset=origin_asset,
                            spend_amount=origin_amount,
                            receive_asset=destination_asset,
                            receive_amount=destination_amount,
                            fee_asset=fee_asset,
                            fee_amount=fee,
                            spend_notes=notes,
                        ),
                    )
                else:
                    raise SkippedCSVEntry(f'Trade destination amount is {destination_amount}.')
        elif origin == 'uphold' and transaction_type == 'out':
            if origin_asset == destination_asset:  # Withdrawals
                events = [AssetMovement(
                    location=Location.UPHOLD,
                    event_type=HistoryEventType.WITHDRAWAL,
                    timestamp=ts_sec_to_ms(timestamp),
                    asset=origin_asset,
                    amount=origin_amount,
                )]
                if fee != ZERO:
                    events.append(AssetMovement(
                        event_identifier=events[0].event_identifier,
                        location=Location.UPHOLD,
                        event_type=HistoryEventType.WITHDRAWAL,
                        timestamp=ts_sec_to_ms(timestamp),
                        asset=fee_asset,
                        amount=fee,
                        is_fee=True,
                    ))
                self.add_history_events(write_cursor, events)
            elif origin_amount > 0:  # Trades (sell)
                self.add_history_events(
                    write_cursor=write_cursor,
                    history_events=create_swap_events(
                        timestamp=ts_sec_to_ms(timestamp),
                        location=Location.UPHOLD,
                        spend_asset=origin_asset,
                        spend_amount=origin_amount,
                        receive_asset=destination_asset,
                        receive_amount=destination_amount,
                        fee_asset=fee_asset,
                        spend_notes=notes,
                        fee_amount=fee,
                    ),
                )
            else:
                raise SkippedCSVEntry(f'Trade origin amount is {origin_amount}.')

        elif destination == 'uphold' and transaction_type == 'in':
            if origin_asset == destination_asset:  # Deposits
                events = [AssetMovement(
                    location=Location.UPHOLD,
                    event_type=HistoryEventType.DEPOSIT,
                    timestamp=ts_sec_to_ms(timestamp),
                    asset=origin_asset,
                    amount=origin_amount,
                )]
                if fee != ZERO:
                    events.append(AssetMovement(
                        event_identifier=events[0].event_identifier,
                        location=Location.UPHOLD,
                        event_type=HistoryEventType.DEPOSIT,
                        timestamp=ts_sec_to_ms(timestamp),
                        asset=fee_asset,
                        amount=fee,
                        is_fee=True,
                    ))
                self.add_history_events(write_cursor, events)
            elif destination_amount > 0:  # Trades (buy)
                self.add_history_events(
                    write_cursor=write_cursor,
                    history_events=create_swap_events(
                        timestamp=ts_sec_to_ms(timestamp),
                        location=Location.UPHOLD,
                        spend_asset=origin_asset,
                        spend_amount=origin_amount,
                        receive_asset=destination_asset,
                        receive_amount=destination_amount,
                        fee_asset=fee_asset,
                        fee_amount=fee,
                        spend_notes=notes,
                    ),
                )
            else:
                raise SkippedCSVEntry(f'Trade destination amount is {destination_amount}.')

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from sample CSVs
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    self._consume_uphold_transaction(write_cursor, row, **kwargs)
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
                except SkippedCSVEntry as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=str(e),
                        is_error=False,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
