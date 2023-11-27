import csv
from pathlib import Path
from typing import Any
from uuid import uuid4

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_bitstamp
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.importers.constants import BITSTAMP_EVENT_PREFIX
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import Location, TradeType
from rotkehlchen.utils.misc import ts_sec_to_ms


class BitstampTransactionsImporter(BaseExchangeImporter):
    def _consume_bitstamp_transaction(
            self,
            write_cursor: DBCursor,
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

        amount, amount_symbol = csv_row['Amount'].split(' ')
        event_identifier = f'{BITSTAMP_EVENT_PREFIX}_{uuid4().hex}'

        if csv_row['Type'] == 'Market':
            value_amount, value_symbol = csv_row['Value'].split(' ')
            fee_amount, fee_symbol = csv_row['Fee'].split(' ')
            trade_type = TradeType.deserialize(csv_row['Sub Type'])

            # if trade_type buy
            bought_amount = deserialize_asset_amount(amount)
            sold_amount = deserialize_asset_amount(value_amount)
            bought_currency = asset_from_bitstamp(amount_symbol)
            sold_currency = asset_from_bitstamp(value_symbol)

            if trade_type == TradeType.SELL:
                bought_amount, sold_amount = sold_amount, bought_amount
                sold_currency, bought_currency = bought_currency, sold_currency

            fee_amount = deserialize_fee(fee_amount)
            fee_currency = asset_from_bitstamp(fee_symbol)
            spend_trade_event = HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=0,
                timestamp=timestamp,
                location=Location.BITSTAMP,
                asset=sold_currency,
                balance=Balance(
                    amount=sold_amount,
                    usd_value=ZERO,
                ),
                notes=f'Spend {sold_amount} {sold_currency} as the result of a trade on Bitstamp',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
            )
            receive_trade_event = HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=1,
                timestamp=timestamp,
                location=Location.BITSTAMP,
                asset=bought_currency,
                balance=Balance(
                    amount=bought_amount,
                    usd_value=ZERO,
                ),
                notes=f'Receive {bought_amount} {bought_currency} as the result of a trade on Bitstamp',  # noqa: E501
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
            )
            fee_event = HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=2,
                timestamp=timestamp,
                location=Location.BITSTAMP,
                asset=fee_currency,
                balance=Balance(
                    amount=fee_amount,
                    usd_value=ZERO,
                ),
                notes=f'Fee of {fee_amount} {fee_currency} as the result of a trade on Bitstamp',
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
            )
            self.add_history_events(write_cursor, [
                spend_trade_event,
                receive_trade_event,
                fee_event,
            ])
        elif csv_row['Type'] in {'Deposit', 'Withdrawal'}:
            amount = deserialize_asset_amount(amount)
            asset = asset_from_bitstamp(amount_symbol)
            transaction_type = csv_row['Type']
            if transaction_type == 'Deposit':
                event_type = HistoryEventType.DEPOSIT
                event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            else:
                event_type = HistoryEventType.WITHDRAWAL
                event_subtype = HistoryEventSubType.REMOVE_ASSET
            movement_event = HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=0,
                timestamp=timestamp,
                location=Location.BITSTAMP,
                asset=asset,
                balance=Balance(
                    amount=amount,
                    usd_value=ZERO,
                ),
                notes=f'{transaction_type} of {amount} {asset} on Bitstamp',
                event_type=event_type,
                event_subtype=event_subtype,
            )
            self.add_history_events(write_cursor, [movement_event])

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Import trades from bitstamp.
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_bitstamp_transaction(write_cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During Bitstamp CSV import found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during Bitstamp CSV import. '
                        f'{e!s}. Ignoring entry',
                    )
                except KeyError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Could not find key {e!s} in csv row {row!s} {e!s}. Ignoring entry',
                    )
                except ValueError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Could not parse some values {e!s} in csv row {row!s}',
                    )
