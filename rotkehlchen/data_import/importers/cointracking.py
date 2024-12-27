import csv
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from rotkehlchen.assets.converters import LOCATION_TO_ASSET_MAPPING
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.importers.constants import COINTRACKING_EVENT_PREFIX
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    SkippedCSVEntry,
    UnsupportedCSVEntry,
    detect_duplicate_event,
    hash_csv_row,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.asset_movement import (
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_force_positive,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBWriterClient


def remap_header(fieldnames: list[str]) -> list[str]:
    cur_count = count(1)
    mapping = {1: 'Buy', 2: 'Sell', 3: 'Fee'}
    return [f'Cur.{mapping[next(cur_count)]}' if f.startswith('Cur.') else f for f in fieldnames]


def exchange_row_to_location(entry: str) -> Location:
    """Takes the exchange row entry of Cointracking exported trades list and returns a location"""
    if entry == 'no exchange':
        return Location.EXTERNAL
    if entry == 'Kraken':
        return Location.KRAKEN
    if entry == 'Poloniex':
        return Location.POLONIEX
    if entry == 'Bittrex':
        return Location.BITTREX
    if entry == 'Binance':
        return Location.BINANCE
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
    if entry == 'ETH Transaction':
        raise UnsupportedCSVEntry(
            'Not importing ETH Transactions from Cointracking. Cointracking does not '
            'export enough data for them. Simply enter your ethereum accounts and all '
            'your transactions will be auto imported directly from the chain',
        )
    if entry == 'BTC Transaction':
        raise UnsupportedCSVEntry(
            'Not importing BTC Transactions from Cointracking. Cointracking does not '
            'export enough data for them. Simply enter your BTC accounts and all '
            'your transactions will be auto imported directly from the chain',
        )
    return Location.EXTERNAL


class CointrackingImporter(BaseExchangeImporter):
    """Cointracking CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Cointracking')
        self.usd = A_USD.resolve_to_asset_with_oracles()

    def _consume_cointracking_entry(
            self,
            write_cursor: 'DBWriterClient',
            csv_row: dict[str, Any],
            timestamp_format: str = '%d.%m.%Y %H:%M:%S',
    ) -> None:
        """Consumes a cointracking entry row from the CSV and adds it into the database
        Can raise:
            - DeserializationError if something is wrong with the format of the expected values
            - UnsupportedCSVEntry if importing of this entry is not supported.
            - IndexError if the CSV file is corrupt
            - KeyError if the an expected CSV key is missing
            - UnknownAsset if one of the assets founds in the entry are not supported
        """
        row_type = csv_row['Type']
        timestamp = ts_sec_to_ms(deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr=timestamp_format,
            location='cointracking.info',
        ))
        location = exchange_row_to_location(csv_row['Exchange'])
        asset_resolver = LOCATION_TO_ASSET_MAPPING.get(location, symbol_to_asset_or_token)
        notes = csv_row['Comment']
        if location == Location.EXTERNAL:
            notes += f'. Data from -{csv_row["Exchange"]}- not known by rotki.'

        fee = AssetAmount(
            asset=asset_resolver(csv_row['Cur.Fee']),
            amount=deserialize_fval_or_zero(csv_row['Fee']),
        ) if csv_row['Fee'] != '' else None

        if row_type in {'Gift/Tip', 'Trade', 'Income'}:
            base_asset = asset_resolver(csv_row['Cur.Buy'])
            quote_asset = None if csv_row['Cur.Sell'] == '' else asset_resolver(csv_row['Cur.Sell'])  # noqa: E501
            if quote_asset is None and row_type not in {'Gift/Tip', 'Income'}:
                raise DeserializationError('Got a trade entry with an empty quote asset')

            if quote_asset is None:
                # Really makes no difference as this is just a gift and the amount is zero
                quote_asset = self.usd
            base_amount_bought = deserialize_fval(csv_row['Buy'])
            if base_amount_bought == ZERO:
                raise DeserializationError('Bought amount in trade is zero')

            if csv_row['Sell'] != '-':
                quote_amount_sold = deserialize_fval(csv_row['Sell'])
            else:
                quote_amount_sold = ZERO

            self.add_history_events(
                write_cursor=write_cursor,
                history_events=create_swap_events(
                    timestamp=timestamp,
                    location=location,
                    spend=AssetAmount(asset=quote_asset, amount=quote_amount_sold),
                    receive=AssetAmount(asset=base_asset, amount=base_amount_bought),
                    fee=fee,
                    spend_notes=notes,
                    event_identifier=f'{COINTRACKING_EVENT_PREFIX}{hash_csv_row(csv_row)}',
                ),
            )
        elif row_type in {'Deposit', 'Withdrawal'}:
            if row_type == 'Deposit':
                amount = deserialize_fval(csv_row['Buy'])
                asset = asset_resolver(csv_row['Cur.Buy'])
                movement_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL] = HistoryEventType.DEPOSIT  # noqa: E501
            else:
                amount = deserialize_fval_force_positive(csv_row['Sell'])
                asset = asset_resolver(csv_row['Cur.Sell'])
                movement_type = HistoryEventType.WITHDRAWAL

            self.add_history_events(
                write_cursor=write_cursor,
                history_events=create_asset_movement_with_fee(
                    timestamp=timestamp,
                    location=location,
                    asset=asset,
                    amount=amount,
                    event_type=movement_type,
                    fee=fee,
                ),
            )
        elif row_type == 'Staking':
            amount = deserialize_fval(csv_row['Buy'])
            asset = asset_resolver(csv_row['Cur.Buy'])
            event_type = HistoryEventType.STAKING
            event_subtype = HistoryEventSubType.REWARD

            if detect_duplicate_event(
                event_type=event_type,
                event_subtype=event_subtype,
                amount=amount,
                asset=asset,
                timestamp_ms=timestamp,
                location=location,
                event_prefix=COINTRACKING_EVENT_PREFIX,
                importer=self,
                write_cursor=write_cursor,
            ):
                raise SkippedCSVEntry(f'Staking event for {asset} at {timestamp} already exists in the DB')  # noqa: E501

            event = HistoryEvent(
                event_identifier=f'{COINTRACKING_EVENT_PREFIX}_{uuid4().hex}',
                sequence_index=0,
                timestamp=timestamp,
                location=location,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=asset,
                amount=amount,
                notes=f'Stake reward of {amount} {asset.symbol} in {location!s}',
            )
            self.add_history_events(write_cursor, [event])
        else:
            raise UnsupportedCSVEntry(
                f'Unknown entry type "{row_type}" encountered during cointracking '
                f'data import. Ignoring entry',
            )

    def _import_csv(
            self,
            write_cursor: 'DBWriterClient',
            filepath: Path,
            **kwargs: Any,
    ) -> None:
        """May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.reader(csvfile, delimiter=',', quotechar='"')
            header = remap_header(next(data))
            for index, row_values in enumerate(data, start=1):
                row = dict(zip(header, row_values, strict=True))
                try:
                    self.total_entries += 1
                    self._consume_cointracking_entry(write_cursor, row, **kwargs)
                    self.imported_entries += 1
                except UnknownAsset as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Unknown asset {e.identifier}.',
                        is_error=True,
                    )
                except (IndexError, ValueError):
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg='Unexpected number of columns.',
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
                except SkippedCSVEntry as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=str(e),
                        is_error=False,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
