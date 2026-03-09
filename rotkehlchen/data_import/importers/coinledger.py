import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.converters import LOCATION_TO_ASSET_MAPPING
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.data_import.importers.constants import COINLEDGER_EVENT_PREFIX
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    UnsupportedCSVEntry,
    maybe_set_transaction_extra_data,
)
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


COINLEDGER_TYPE_MAPPINGS: dict[str, tuple[HistoryEventType, HistoryEventSubType]] = {
    'Airdrop': (HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP),
    'Gift Received': (HistoryEventType.RECEIVE, HistoryEventSubType.DONATE),
    'Gift Sent': (HistoryEventType.SPEND, HistoryEventSubType.DONATE),
    'Hard Fork': (HistoryEventType.RECEIVE, HistoryEventSubType.NONE),
    'Interest': (HistoryEventType.RECEIVE, HistoryEventSubType.INTEREST),
    'Interest Payment': (HistoryEventType.RECEIVE, HistoryEventSubType.INTEREST),
    'Investment Loss': (HistoryEventType.LOSS, HistoryEventSubType.NONE),
    'Merchant Payment': (HistoryEventType.SPEND, HistoryEventSubType.PAYMENT),
    'Mining': (HistoryEventType.RECEIVE, HistoryEventSubType.REWARD),
    'Network Fee': (HistoryEventType.SPEND, HistoryEventSubType.FEE),
    'Staking': (HistoryEventType.STAKING, HistoryEventSubType.REWARD),
    'Theft Loss': (HistoryEventType.LOSS, HistoryEventSubType.HACK),
}

COINLEDGER_POSITIVE_ONLY_TYPES = {
    'Airdrop',
    'Gift Received',
    'Hard Fork',
    'Mining',
    'Staking',
}
COINLEDGER_NEGATIVE_ONLY_TYPES = {
    'Gift Sent',
    'Investment Loss',
    'Merchant Payment',
    'Network Fee',
    'Theft Loss',
}

FEE_RECORD_TYPES = {'Network Fee', 'Platform Fee'}


def platform_row_to_location(entry: str) -> Location:
    """Takes the Platform value from CoinLedger and returns a location."""
    try:
        return Location.deserialize(entry)
    except DeserializationError:
        pass

    # Map common exchange names to rotki locations
    if entry == 'Binance Smart Chain':
        return Location.BINANCE_SC
    if entry == 'Binance':
        return Location.BINANCE
    if entry == 'Kraken':
        return Location.KRAKEN
    if entry == 'Poloniex':
        return Location.POLONIEX
    if entry == 'Bittrex':
        return Location.BITTREX
    if entry == 'Bitmex':
        return Location.BITMEX
    if entry == 'Coinbase':
        return Location.COINBASE
    if entry in {'CoinbasePro', 'GDAX'}:
        return Location.COINBASEPRO
    if entry == 'Gemini':
        return Location.GEMINI
    if entry == 'Bitstamp':
        return Location.BITSTAMP
    if entry == 'Bitfinex':
        return Location.BITFINEX
    if entry == 'KuCoin':
        return Location.KUCOIN

    log.warning(f'Coinledger location "{entry}" unrecognized and imported as external')
    return Location.EXTERNAL


class CoinledgerImporter(BaseExchangeImporter):
    """CoinLedger CSV importer."""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='CoinLedger')
        self._group_sequence_index: dict[str, int] = {}

    def reset(self) -> None:
        super().reset()
        self._group_sequence_index = {}

    def _consume_coinledger_entry(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%Y-%m-%dT%H:%M:%S.%f',
    ) -> None:
        """Consumes a CoinLedger CSV row and adds it into the database.

        Can raise:
            - DeserializationError if expected values are malformed
            - UnsupportedCSVEntry if the row is unsupported
            - KeyError if an expected CSV key is missing
            - UnknownAsset if one of the assets in the row is not supported
        """
        timestamp = ts_sec_to_ms(deserialize_timestamp_from_date(
            date=csv_row['Timestamp (UTC)'],
            formatstr=timestamp_format,
            location='CoinLedger',
        ))
        location = platform_row_to_location(csv_row['Platform'])
        asset_resolver = LOCATION_TO_ASSET_MAPPING.get(location, symbol_to_asset_or_token)
        asset = asset_resolver(csv_row['Asset'])
        raw_amount = deserialize_fval(csv_row['Amount'])
        amount = abs(raw_amount)
        row_type = csv_row['Type']
        record_type = csv_row['Record Type']
        internal_id = csv_row['Internal Id']
        transaction_id = csv_row['Blockchain Id'] or csv_row['Platform Id'] or None
        extra_data = maybe_set_transaction_extra_data(address=None, transaction_id=transaction_id)
        notes = (
            f'{row_type} ({record_type}) from CoinLedger'
            if csv_row['Description'] == ''
            else f'{row_type} ({record_type}) from CoinLedger: {csv_row["Description"]}'
        )

        if row_type in {'Deposit', 'Withdrawal'} and record_type in {'Credit', 'Debit'}:
            movement_subtype: Literal[
                HistoryEventSubType.RECEIVE,
                HistoryEventSubType.SPEND,
            ]
            if record_type == 'Credit':
                movement_subtype = HistoryEventSubType.RECEIVE
            else:
                movement_subtype = HistoryEventSubType.SPEND
            self.add_history_events(write_cursor, [AssetMovement(
                timestamp=timestamp,
                location=location,
                event_subtype=movement_subtype,
                asset=asset,
                amount=amount,
                unique_id=internal_id,
                extra_data=extra_data,
                location_label=csv_row['Account Name'] or None,
                notes=notes,
            )])
            return

        if row_type in COINLEDGER_TYPE_MAPPINGS:
            if row_type in {'Interest', 'Interest Payment'} and raw_amount < 0:
                event_type = HistoryEventType.SPEND
                event_subtype = HistoryEventSubType.NONE
            else:
                if row_type in COINLEDGER_POSITIVE_ONLY_TYPES and raw_amount < 0:
                    raise UnsupportedCSVEntry(
                        f'Contradictory amount sign for "{row_type}" in coinledger data import. '
                        f'Expected non-negative amount but got {raw_amount}. Ignoring entry',
                    )
                if row_type in COINLEDGER_NEGATIVE_ONLY_TYPES and raw_amount > 0:
                    raise UnsupportedCSVEntry(
                        f'Contradictory amount sign for "{row_type}" in coinledger data import. '
                        f'Expected non-positive amount but got {raw_amount}. Ignoring entry',
                    )
                event_type, event_subtype = COINLEDGER_TYPE_MAPPINGS[row_type]
        elif record_type == 'Credit':
            event_type = HistoryEventType.RECEIVE
            event_subtype = HistoryEventSubType.NONE
        elif record_type in {'Debit', *FEE_RECORD_TYPES}:
            event_type = HistoryEventType.SPEND
            event_subtype = (
                HistoryEventSubType.FEE
                if record_type in FEE_RECORD_TYPES
                else HistoryEventSubType.NONE
            )
        elif record_type == 'Margin Gain':
            if raw_amount < 0:
                event_type = HistoryEventType.LOSS
                event_subtype = HistoryEventSubType.NONE
            else:
                event_type = HistoryEventType.RECEIVE
                event_subtype = HistoryEventSubType.NONE
        else:
            raise UnsupportedCSVEntry(
                f'Unknown record type "{record_type}" encountered during coinledger data import. '
                f'Ignoring entry',
            )

        group_identifier = f'{COINLEDGER_EVENT_PREFIX}_{internal_id}'
        sequence_index = self._group_sequence_index.get(group_identifier, 0)
        self._group_sequence_index[group_identifier] = sequence_index + 1
        history_extra_data = None if extra_data is None else dict(extra_data)
        self.add_history_events(write_cursor, [HistoryEvent(
            group_identifier=group_identifier,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            extra_data=history_extra_data,
            location_label=csv_row['Account Name'] or None,
            notes=notes,
        )])

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """Import transactions from CoinLedger CSV exports."""
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile, delimiter=',', quotechar='"')
            for index, row in enumerate(data, start=1):
                self.total_entries += 1
                try:
                    self._consume_coinledger_entry(write_cursor, row, **kwargs)
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
