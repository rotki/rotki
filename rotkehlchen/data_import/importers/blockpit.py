import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import LOCATION_TO_ASSET_MAPPING
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.importers.constants import BLOCKPIT_EVENT_PREFIX
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry, hash_csv_row
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def exchange_row_to_location(entry: str) -> Location:
    """Takes the Source Name from blockpit and returns a location"""
    try:
        return Location.deserialize(entry)  # Should get everything without spaces or periods
    except DeserializationError:
        if entry == 'Binance US':
            return Location.BINANCEUS
        if entry == 'Bitcoin.de':
            return Location.BITCOINDE
        if entry == 'Coinbase Pro':
            return Location.COINBASEPRO
        if entry in {'Crypto.com App', 'Crypto.com Exchange'}:
            return Location.CRYPTOCOM
        if entry == 'WOO X':
            return Location.WOO
        return Location.EXTERNAL


class BlockpitImporter(BaseExchangeImporter):
    """Blockpit CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Blockpit')

    def _consume_blockpit_transaction(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            fee_currency: AssetWithOracles,
            timestamp_format: str = '%d.%m.%Y %H:%M',
    ) -> None:
        """Consume a blockpit entry row from the CSV and add it into the database
        Can raise:
            - DeserializationError if something is wrong with the format of the expected values
            - UnsupportedCSVEntry if importing of this entry is not supported.
            - KeyError if an expected CSV key is missing
            - UnknownAsset if one of the assets found in the entry are not supported
        """
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Timestamp'],
            formatstr=timestamp_format,
            location='Blockpit',
        )
        source_name = csv_row['Source Name']
        transaction_type = csv_row['Transaction Type']
        location = exchange_row_to_location(source_name)
        asset_resolver = LOCATION_TO_ASSET_MAPPING.get(
            location if location in LOCATION_TO_ASSET_MAPPING else Location.EXTERNAL,
            symbol_to_asset_or_token,
        )

        fee_amount = ZERO
        if csv_row['Fee Asset'] != '':
            fee_amount = deserialize_fval_or_zero(csv_row['Fee Amount'])
            fee_currency = asset_resolver(csv_row['Fee Asset'])
        notes = csv_row['Note']

        if transaction_type == 'Trade':
            if (amount_in := deserialize_fval(csv_row['Incoming Amount'])) == ZERO:
                raise DeserializationError('Incoming amount in trade is zero.')

            self.add_history_events(
                write_cursor=write_cursor,
                history_events=create_swap_events(
                    timestamp=ts_sec_to_ms(timestamp),
                    location=location,
                    spend=AssetAmount(
                        asset=asset_resolver(csv_row['Outgoing Asset']),
                        amount=deserialize_fval(csv_row['Outgoing Amount']),
                    ),
                    receive=AssetAmount(
                        asset=asset_resolver(csv_row['Incoming Asset']),
                        amount=amount_in,
                    ),
                    fee=AssetAmount(
                        asset=fee_currency,
                        amount=fee_amount,
                    ),
                    spend_notes=notes,
                    group_identifier=f'{BLOCKPIT_EVENT_PREFIX}{hash_csv_row(csv_row)}',
                ),
            )
        elif transaction_type in {'Deposit', 'Withdrawal', 'NonTaxableIn', 'NonTaxableOut'}:
            if transaction_type in {'Deposit', 'NonTaxableIn'}:
                direction = 'Incoming'
                movement_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL] = HistoryEventType.DEPOSIT  # noqa: E501
            else:
                direction = 'Outgoing'
                movement_type = HistoryEventType.WITHDRAWAL

            events = [AssetMovement(
                location=location,
                event_type=movement_type,
                timestamp=ts_sec_to_ms(timestamp),
                asset=asset_resolver(csv_row[f'{direction} Asset']),
                amount=deserialize_fval(csv_row[f'{direction} Amount']),
            )]
            if fee_amount != ZERO:
                events.append(AssetMovement(
                    group_identifier=events[0].group_identifier,
                    location=location,
                    event_type=movement_type,
                    timestamp=ts_sec_to_ms(timestamp),
                    asset=fee_currency,
                    amount=fee_amount,
                    is_fee=True,
                ))
            self.add_history_events(write_cursor, events)

        elif transaction_type in {
            'Airdrop',
            'Bounties',
            'Staking',
            'Lending',
            'Fee',
            'Gift',
            'Margin_trading_loss',
            'Margin_trading_profit',
        }:
            timestamp_ms = ts_sec_to_ms(timestamp)

            if transaction_type in {'Fee', 'Gift', 'Margin_trading_loss'}:
                asset = asset_resolver(csv_row['Outgoing Asset'])
                amount = deserialize_fval(csv_row['Outgoing Amount'])
                event_type = HistoryEventType.SPEND
                event_subtype = HistoryEventSubType.NONE
                event_description = 'Spend'
            else:
                asset = asset_resolver(csv_row['Incoming Asset'])
                amount = deserialize_fval(csv_row['Incoming Amount'])
                event_type = HistoryEventType.RECEIVE
                event_subtype = HistoryEventSubType.NONE
                event_description = 'Receive'

            if transaction_type == 'Staking':
                event_type = HistoryEventType.STAKING
                event_subtype = HistoryEventSubType.REWARD
                event_description = 'Staking reward of'
            elif transaction_type == 'Fee':
                event_subtype = HistoryEventSubType.FEE
                event_description = 'Fee of'

            event = HistoryEvent(
                group_identifier=f'{BLOCKPIT_EVENT_PREFIX}_{uuid4().hex}',
                sequence_index=1,
                timestamp=timestamp_ms,
                location=location,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=asset,
                amount=amount,
                notes=f'{event_description} {amount} {asset.symbol} in {location!s}',
            )

            if csv_row['Fee Asset'] != '':
                fee_event = HistoryEvent(
                    group_identifier=f'{BLOCKPIT_EVENT_PREFIX}_{uuid4().hex}',
                    sequence_index=0,
                    timestamp=timestamp_ms,
                    location=location,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=fee_currency,
                    amount=fee_amount,
                    notes=f'Fee of {fee_amount} {fee_currency.symbol} in {location!s}',
                )
                self.add_history_events(write_cursor, [fee_event, event])
            else:
                self.add_history_events(write_cursor, [event])
        else:
            raise UnsupportedCSVEntry(
                f'Unknown entry type "{transaction_type}" encountered during blockpit '
                f'data import. Ignoring entry',
            )

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """Import transactions from blockpit."""
        usd = A_USD.resolve_to_asset_with_oracles()
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile, delimiter=';')
            for index, row in enumerate(data, start=1):
                try:
                    self.total_entries += 1
                    self._consume_blockpit_transaction(write_cursor, row, usd, **kwargs)
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
