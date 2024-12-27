import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from rotkehlchen.assets.converters import asset_from_bitstamp
from rotkehlchen.data_import.importers.constants import BITSTAMP_EVENT_PREFIX
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.client import DBWriterClient
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
)
from rotkehlchen.history.events.structures.swap import (
    create_swap_events,
    deserialize_trade_type_is_buy,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Location, Price
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


class BitstampTransactionsImporter(BaseExchangeImporter):
    """Bitstamp CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Bitstamp')

    def _consume_bitstamp_transaction(
            self,
            write_cursor: DBWriterClient,
            csv_row: dict[str, Any],
            timestamp_format: str = '%b. %d, %Y, %I:%M %p',
    ) -> None:
        """
        Consume the file containing only trades from Bitstamp.
        - UnknownAsset
        - DeserializationError
        - KeyError
        - ValueError
        """
        timestamp = ts_sec_to_ms(deserialize_timestamp_from_date(
            date=csv_row['Datetime'],
            formatstr=timestamp_format,
            location='Bitstamp',
        ))

        events: list[HistoryBaseEntry] = []
        amount, amount_symbol = csv_row['Amount'].split(' ')
        event_identifier = f'{BITSTAMP_EVENT_PREFIX}_{uuid4().hex}'
        if csv_row['Type'] == 'Market':
            value_str, value_symbol = csv_row['Value'].split(' ')
            fee_str, fee_symbol = csv_row['Fee'].split(' ')
            spend, receive = get_swap_spend_receive(
                is_buy=deserialize_trade_type_is_buy(csv_row['Sub Type']),
                base_asset=asset_from_bitstamp(amount_symbol),
                quote_asset=asset_from_bitstamp(value_symbol),
                amount=(swap_amount := deserialize_fval(amount)),
                rate=Price(deserialize_fval(value_str) / swap_amount),
            )
            events.extend(create_swap_events(
                timestamp=timestamp,
                spend=spend,
                location=Location.BITSTAMP,
                receive=receive,
                event_identifier=event_identifier,
                fee=AssetAmount(
                    asset=asset_from_bitstamp(fee_symbol),
                    amount=deserialize_fval_or_zero(fee_str),
                ),
            ))
        elif csv_row['Type'] in {'Deposit', 'Withdrawal'}:
            events.append(AssetMovement(
                event_identifier=event_identifier,
                event_type=HistoryEventType.DEPOSIT if csv_row['Type'] == 'Deposit' else HistoryEventType.WITHDRAWAL,  # noqa: E501
                timestamp=timestamp,
                location=Location.BITSTAMP,
                asset=asset_from_bitstamp(amount_symbol),
                amount=deserialize_fval(amount),
            ))

        if len(events) > 0:
            self.add_history_events(
                write_cursor=write_cursor,
                history_events=events,
            )

    def _import_csv(self, write_cursor: DBWriterClient, filepath: Path, **kwargs: Any) -> None:
        """
        Import trades from bitstamp.
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    self._consume_bitstamp_transaction(write_cursor, row, **kwargs)
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
                except ValueError as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Could not parse some values: {e!s}',
                        is_error=True,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
