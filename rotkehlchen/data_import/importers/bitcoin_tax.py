import csv
import hashlib
import logging
from pathlib import Path
from typing import Any, Literal, Optional

from rotkehlchen.accounting.structures.balance import AssetBalance, Balance
from rotkehlchen.accounting.structures.base import HistoryEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.converters import LOCATION_TO_ASSET_MAPPING, asset_from_common_identifier
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import Fee, Location, TimestampMS
from rotkehlchen.utils.misc import ts_sec_to_ms

from .constants import ROTKI_EVENT_PREFIX

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CSVType = Literal['trades', 'other_events']

ACTION_TO_HISTORY_EVENT_TYPE = {
    'INCOME': (HistoryEventType.RECEIVE, HistoryEventSubType.NONE),
    'MINING': (HistoryEventType.RECEIVE, HistoryEventSubType.REWARD),
    'GIFTIN': (HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP),
    'BORROW': (HistoryEventType.RECEIVE, HistoryEventSubType.GENERATE_DEBT),
    'SPEND': (HistoryEventType.SPEND, HistoryEventSubType.NONE),
    'DONATION': (HistoryEventType.SPEND, HistoryEventSubType.DONATE),
    'GIFT': (HistoryEventType.SPEND, HistoryEventSubType.NONE),
    'STOLEN': (HistoryEventType.SPEND, HistoryEventSubType.NONE),
    'LOST': (HistoryEventType.SPEND, HistoryEventSubType.NONE),
    'REPAY': (HistoryEventType.SPEND, HistoryEventSubType.PAYBACK_DEBT),
}


def hash_csv_row(csv_row: dict[str, Any]) -> str:
    """Convert the row to string and encode it to a hex string to get a unique hash"""
    row_str = str(csv_row).encode()
    return hashlib.sha256(row_str).hexdigest()


def determine_csv_type(csv_data: csv.DictReader) -> CSVType:
    if csv_data.fieldnames is None:
        raise InputError('Empty Bitcoin_Tax csv file')
    if 'Cost/Proceeds' in csv_data.fieldnames:
        return 'trades'
    return 'other_events'


class BitcoinTaxImporter(BaseExchangeImporter):
    def _consume_trade_event(
            self,
            cursor: DBCursor,
            csv_row: dict[str, Any],
            event_identifier: str,
            timestamp: TimestampMS,
            location: Location,
            action: str,
            base_asset_balance: AssetBalance,
            quote_asset_balance: AssetBalance,
            fee_asset_balance: Optional[AssetBalance],
            memo: str,
    ) -> None:
        """
        Consumes a trade event from the Bitcoin_Tax csv file and creates the corresponding
        history events that describe it. It creates 2 or 3 history events depending
        on the presence of a fee.

        May raise:
        - UnsupportedCSVEntry: When the action is not supported
        """
        if action not in ('BUY', 'SELL', 'SWAP'):
            raise UnsupportedCSVEntry(f'Unsupported entry action type {action}. Data: {csv_row}')
        if action == 'SWAP':
            # The SWAP action is used by bitcoin tax when a crypto asset is renamed or forked.
            log.info('SWAP action is skipped. Forks and renames are handled by rotki elsewhere.')
            return

        # BUY action
        receive_asset_balance = base_asset_balance
        spend_asset_balance = quote_asset_balance
        if action == 'SELL':
            receive_asset_balance = quote_asset_balance
            spend_asset_balance = base_asset_balance

        spend_event = HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=0,
            timestamp=timestamp,
            location=location,
            asset=spend_asset_balance.asset,
            balance=spend_asset_balance.balance,
            notes=memo,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
        )
        receive_event = HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=1,
            timestamp=timestamp,
            location=location,
            asset=receive_asset_balance.asset,
            balance=receive_asset_balance.balance,
            notes=memo,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
        )
        self.add_history_events(cursor, [spend_event, receive_event])
        if fee_asset_balance is not None:
            fee_event = HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=2,
                timestamp=timestamp,
                location=location,
                asset=fee_asset_balance.asset,
                balance=fee_asset_balance.balance,
                notes=memo,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
            )
            self.add_history_events(cursor, [fee_event])

    def _consume_income_spending_event(
            self,
            cursor: DBCursor,
            csv_row: dict[str, Any],
            event_identifier: str,
            timestamp: TimestampMS,
            location: Location,
            action: str,
            asset_balance: AssetBalance,
            fee_asset_balance: Optional[AssetBalance],
            memo: str,
    ) -> None:
        """
        Consumes an income or a spending event from the Bitcoin_Tax csv file
        and creates the corresponding history events that describe it. It creates 1 or 2
        history events depending on the presence of a fee.

        May raise:
        - UnsupportedCSVEntry: When the action is not supported
        """
        if action not in ACTION_TO_HISTORY_EVENT_TYPE:
            raise UnsupportedCSVEntry(f'Unsupported entry action type {action}. Data: {csv_row}')

        event_type, event_subtype = ACTION_TO_HISTORY_EVENT_TYPE[action]
        event = HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=0,
            timestamp=timestamp,
            location=location,
            asset=asset_balance.asset,
            balance=asset_balance.balance,
            notes=memo,
            event_type=event_type,
            event_subtype=event_subtype,
        )
        self.add_history_events(cursor, [event])
        if fee_asset_balance is not None:
            fee_event = HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=1,
                timestamp=timestamp,
                location=location,
                asset=fee_asset_balance.asset,
                balance=fee_asset_balance.balance,
                notes=memo,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
            )
            self.add_history_events(cursor, [fee_event])

    def _consume_event(
            self,
            cursor: DBCursor,
            csv_row: dict[str, Any],
            csv_type: CSVType,
            timestamp_format: str = '%Y-%m-%d %H:%M:%S %z',
    ) -> None:
        """
        Consumes a single event from a Bitcoin_Tax csv file.
        Supported file types are: trades, income, spending.
        Income and spending have identical structure.

        May raise:
        - UnknownAsset
        - DeserializationError
        - UnsupportedCSVEntry
        """
        if all(value == '' for value in csv_row.values()):
            return  # skip empty rows

        # use a deterministic event_identifier to avoid duplicate events in case of reimport
        event_identifier = f'{ROTKI_EVENT_PREFIX}BTX_{hash_csv_row(csv_row)}'
        timestamp = ts_sec_to_ms(deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr=timestamp_format,
            location='Bitcoin_Tax',
        ))

        try:
            location = Location.deserialize(csv_row['Account'])
        except DeserializationError:
            location = Location.EXTERNAL
            if csv_row['Account'] in ('Coinbase Pro', 'GDAX'):
                location = Location.COINBASEPRO

        asset_resolver = LOCATION_TO_ASSET_MAPPING.get(location, asset_from_common_identifier)
        base_asset = asset_resolver(csv_row['Symbol'])
        base_asset_amount = deserialize_asset_amount(csv_row['Volume'])
        fee_amount = Fee(deserialize_asset_amount(csv_row['Fee'])) if csv_row['Fee'] else Fee(ZERO)  # noqa: E501
        fee_asset = (
            asset_resolver(csv_row['FeeCurrency'])
            if csv_row['FeeCurrency'] and fee_amount is not None else None
        )
        action = csv_row['Action']
        memo = f"Imported description from bitcoin tax: {csv_row['Memo']}" if csv_row['Memo'] else ''  # noqa: E501

        base_asset_balance = AssetBalance(base_asset, Balance(base_asset_amount, ZERO))
        fee_asset_balance = None
        if fee_amount != ZERO and fee_asset is not None:
            fee_asset_balance = AssetBalance(fee_asset, Balance(fee_amount, ZERO))

        if csv_type == 'trades':
            quote_asset = asset_resolver(csv_row['Currency'])
            quote_asset_amount = deserialize_asset_amount(csv_row['Cost/Proceeds'])
            quote_asset_balance = AssetBalance(quote_asset, Balance(quote_asset_amount, ZERO))
            self._consume_trade_event(
                cursor=cursor,
                csv_row=csv_row,
                event_identifier=event_identifier,
                timestamp=timestamp,
                location=location,
                action=action,
                base_asset_balance=base_asset_balance,
                quote_asset_balance=quote_asset_balance,
                fee_asset_balance=fee_asset_balance,
                memo=memo,
            )
            return
        # else
        self._consume_income_spending_event(
            cursor=cursor,
            csv_row=csv_row,
            event_identifier=event_identifier,
            timestamp=timestamp,
            location=location,
            action=action,
            asset_balance=base_asset_balance,
            fee_asset_balance=fee_asset_balance,
            memo=memo,
        )

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            csv_type = determine_csv_type(data)
            for _, row in enumerate(data):
                try:
                    self._consume_event(cursor, row, csv_type, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During Bitcoin_Tax csv import found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during Bitcoin_Tax csv import. '
                        f'{e!s}. Ignoring entry',
                    )
                except UnsupportedCSVEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
