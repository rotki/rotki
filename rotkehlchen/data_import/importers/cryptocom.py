import csv
import functools
import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.converters import asset_from_cryptocom
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    SkippedCSVEntry,
    UnsupportedCSVEntry,
    hash_csv_row,
)
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_force_positive,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Fee, Location, Timestamp
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


CRYPTOCOM_PREFIX = 'CCM_'
INDEX = '_index'


def hash_csv_row_without_index(csv_row: Any) -> str:
    """Hash the CSV row excluding the INDEX"""
    return hash_csv_row({k: v for k, v in csv_row.items() if k != INDEX})


class CryptocomImporter(BaseExchangeImporter):
    """Crypto.com CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Crypto.com')

    def _consume_cryptocom_entry(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%Y-%m-%d %H:%M:%S',
    ) -> None:
        """Consumes a cryptocom entry row from the CSV and adds it into the database
        Can raise:
            - DeserializationError if something is wrong with the format of the expected values
            - UnsupportedCryptocomEntry if importing of this entry is not supported.
            - KeyError if the expected CSV key is missing
            - UnknownAsset if one of the assets founds in the entry are not supported
        """
        row_type = csv_row['Transaction Kind']
        timestamp = ts_sec_to_ms(deserialize_timestamp_from_date(
            date=csv_row['Timestamp (UTC)'],
            formatstr=timestamp_format,
            location='cryptocom',
        ))
        description = csv_row['Transaction Description']
        notes = f'{description}\nSource: crypto.com (CSV import)'

        # No fees info until (Nov 2020) on crypto.com
        # fees are not displayed in the export data
        fee = Fee(ZERO)
        fee_currency = A_USD  # whatever (used only if there is no fee)

        if row_type in {
            'crypto_purchase',
            'crypto_exchange',
            'viban_purchase',
            'crypto_viban_exchange',
            'recurring_buy_order',
            'card_top_up',
        }:
            # variable mapping to raw data
            currency = csv_row['Currency']
            to_currency = csv_row['To Currency']
            native_currency = csv_row['Native Currency']
            amount = csv_row['Amount']
            to_amount = csv_row['To Amount']
            native_amount = csv_row['Native Amount']

            if row_type in {
                'crypto_exchange',
                'crypto_viban_exchange',
                'recurring_buy_order',
                'viban_purchase',
            }:
                # trades (fiat, crypto) to (crypto, fiat)
                base_asset = asset_from_cryptocom(to_currency)
                quote_asset = asset_from_cryptocom(currency)
                if quote_asset is None:
                    raise DeserializationError('Got a trade entry with an empty quote asset')
                base_amount_bought = deserialize_fval(to_amount)
                quote_amount_sold = deserialize_fval(amount)
            elif row_type == 'card_top_up':
                quote_asset = asset_from_cryptocom(currency)
                base_asset = asset_from_cryptocom(native_currency)
                base_amount_bought = deserialize_fval_force_positive(native_amount)
                quote_amount_sold = deserialize_fval_force_positive(amount)
            else:
                base_asset = asset_from_cryptocom(currency)
                quote_asset = asset_from_cryptocom(native_currency)
                base_amount_bought = deserialize_fval(amount)
                quote_amount_sold = deserialize_fval(native_amount)

            self.add_history_events(
                write_cursor=write_cursor,
                history_events=create_swap_events(
                    event_identifier=f'{CRYPTOCOM_PREFIX}{hash_csv_row_without_index(csv_row)}',
                    timestamp=timestamp,
                    spend=AssetAmount(asset=quote_asset, amount=abs(quote_amount_sold)),
                    receive=AssetAmount(asset=base_asset, amount=abs(base_amount_bought)),
                    fee=AssetAmount(asset=fee_currency, amount=fee),
                    location=Location.CRYPTOCOM,
                    spend_notes=notes,
                ),
            )

        elif row_type in {
            'crypto_withdrawal',
            'crypto_deposit',
            'viban_deposit',
            'viban_card_top_up',
        }:
            if row_type in {'crypto_withdrawal', 'viban_deposit', 'viban_card_top_up'}:
                movement_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL] = HistoryEventType.WITHDRAWAL  # noqa: E501
                amount = deserialize_fval_force_positive(csv_row['Amount'])
            else:
                movement_type = HistoryEventType.DEPOSIT
                amount = deserialize_fval(csv_row['Amount'])

            asset = asset_from_cryptocom(csv_row['Currency'])
            self.add_history_events(write_cursor, [AssetMovement(
                location=Location.CRYPTOCOM,
                event_type=movement_type,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
            )])
        elif row_type in {
            'airdrop_to_exchange_transfer',
            'mco_stake_reward',
            'crypto_payment_refund',
            'pay_checkout_reward'
            'transfer_cashback',
            'rewards_platform_deposit_credited',
            'pay_checkout_reward',
            'transfer_cashback',
            'supercharger_reward_to_app_credited',
            'referral_card_cashback',
            'referral_gift',
            'referral_bonus',
            'crypto_earn_interest_paid',
            'reimbursement',
        }:
            asset = asset_from_cryptocom(csv_row['Currency'])
            amount = deserialize_fval(csv_row['Amount'])
            event = HistoryEvent(
                event_identifier=f'{CRYPTOCOM_PREFIX}{hash_csv_row(csv_row)}',
                sequence_index=0,
                timestamp=timestamp,
                location=Location.CRYPTOCOM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                amount=amount,
                asset=asset,
                notes=notes,
            )
            self.add_history_events(write_cursor, [event])
        elif row_type in {'crypto_payment', 'reimbursement_reverted', 'card_cashback_reverted'}:
            asset = asset_from_cryptocom(csv_row['Currency'])
            amount = abs(deserialize_fval(csv_row['Amount']))
            event = HistoryEvent(
                event_identifier=f'{CRYPTOCOM_PREFIX}{hash_csv_row(csv_row)}',
                sequence_index=0,
                timestamp=timestamp,
                location=Location.CRYPTOCOM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                amount=amount,
                asset=asset,
                notes=notes,
            )
            self.add_history_events(write_cursor, [event])
        elif row_type == 'invest_deposit':
            asset = asset_from_cryptocom(csv_row['Currency'])
            amount = abs(deserialize_fval(csv_row['Amount']))
            self.add_history_events(write_cursor, [AssetMovement(
                location=Location.CRYPTOCOM,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
            )])
        elif row_type == 'invest_withdrawal':
            asset = asset_from_cryptocom(csv_row['Currency'])
            amount = deserialize_fval(csv_row['Amount'])
            self.add_history_events(write_cursor, [AssetMovement(
                location=Location.CRYPTOCOM,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
            )])
        elif row_type == 'crypto_transfer':
            asset = asset_from_cryptocom(csv_row['Currency'])
            amount = deserialize_fval(csv_row['Amount'])
            if amount < 0:
                event_type = HistoryEventType.SPEND
                amount = abs(amount)
            else:
                event_type = HistoryEventType.RECEIVE

            event = HistoryEvent(
                event_identifier=f'{CRYPTOCOM_PREFIX}{hash_csv_row(csv_row)}',
                sequence_index=0,
                timestamp=timestamp,
                location=Location.CRYPTOCOM,
                event_type=event_type,
                event_subtype=HistoryEventSubType.NONE,
                amount=amount,
                asset=asset,
                notes=notes,
            )
            self.add_history_events(write_cursor, [event])
        elif row_type in {
            'crypto_earn_program_created',
            'crypto_earn_program_withdrawn',
            'lockup_lock',
            'lockup_unlock',
            'dynamic_coin_swap_bonus_exchange_deposit',
            'crypto_wallet_swap_debited',
            'crypto_wallet_swap_credited',
            'lockup_swap_debited',
            'lockup_swap_credited',
            'lockup_swap_rebate',
            # we don't handle crypto.com exchange yet
            'crypto_to_exchange_transfer',
            'exchange_to_crypto_transfer',
            # supercharger actions
            'supercharger_deposit',
            'supercharger_withdrawal',
            # The user has received an airdrop but can't claim it yet
            'airdrop_locked',
        }:
            raise SkippedCSVEntry("Entry doesn't affect wallet balance")
        elif row_type in {
            'dynamic_coin_swap_debited',
            'dynamic_coin_swap_credited',
            'dust_conversion_debited',
            'dust_conversion_credited',
            'interest_swap_credited',
            'interest_swap_debited',
        }:
            # already handled using _import_cryptocom_associated_entries
            raise SkippedCSVEntry
        else:
            raise UnsupportedCSVEntry(
                f'Unknown entrype type "{row_type}" encountered during '
                f'cryptocom data import. Ignoring entry',
            )

    def _import_cryptocom_associated_entries(
            self,
            write_cursor: DBCursor,
            data: Any,
            tx_kind: str,
            timestamp_format: str = '%Y-%m-%d %H:%M:%S',
    ) -> None:
        """Look for events that have associated entries and handle them as trades.

        This method looks for `*_debited` and `*_credited` entries using the
        same timestamp to handle them as one trade.

        Known kind: 'dynamic_coin_swap' or 'dust_conversion'

        May raise:
        - UnknownAsset if an unknown asset is encountered in the imported files
        - KeyError if a row contains unexpected data entries
        """
        multiple_rows: dict[Any, dict[str, Any]] = {}
        investments_deposits: dict[str, list[Any]] = defaultdict(list)
        investments_withdrawals: dict[str, list[Any]] = defaultdict(list)
        credited_row = None
        expects_debited = False
        credited_timestamp = None
        for index, row in enumerate(data, start=1):
            log.debug(f'Processing cryptocom row at {row["Timestamp (UTC)"]} and type {tx_kind}')
            row[INDEX] = index
            # If we don't have the corresponding debited entry ignore them
            # and warn the user
            if (
                expects_debited is True and
                row['Transaction Kind'] != f'{tx_kind}_debited'
            ):
                self.send_message(
                    row_index=index,
                    csv_row=row,
                    msg=f'Found {tx_kind}_credited but no amount debited afterwards at date {row["Timestamp (UTC)"]}',  # noqa: E501
                    is_error=True,
                )
                # Pop the last credited event as it's invalid. We always assume to be at least
                # one debited event and one credited event. If we don't find the debited event
                # we have to remove the credit at the right timestamp or our logic will break.
                # We notify the user about this issue so (s)he can take actions.
                multiple_rows.pop(credited_timestamp, None)
                # reset expects_debited value
                expects_debited = False
            if row['Transaction Kind'] == f'{tx_kind}_debited':
                timestamp = deserialize_timestamp_from_date(
                    date=row['Timestamp (UTC)'],
                    formatstr=timestamp_format,
                    location='cryptocom',
                )
                if expects_debited is False and timestamp != credited_timestamp:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Found {tx_kind}_debited but no amount credited before at date {row["Timestamp (UTC)"]}',  # noqa: E501
                        is_error=True,
                    )
                    continue
                if timestamp not in multiple_rows:
                    multiple_rows[timestamp] = {}
                if 'debited' not in multiple_rows[timestamp]:
                    multiple_rows[timestamp]['debited'] = []
                multiple_rows[timestamp]['debited'].append(row)
                expects_debited = False
            elif row['Transaction Kind'] == f'{tx_kind}_credited':
                # The only is one credited row
                timestamp = deserialize_timestamp_from_date(
                    date=row['Timestamp (UTC)'],
                    formatstr=timestamp_format,
                    location='cryptocom',
                )
                if timestamp not in multiple_rows:
                    multiple_rows[timestamp] = {}
                expects_debited = True
                credited_timestamp = timestamp
                multiple_rows[timestamp]['credited'] = row
            elif row['Transaction Kind'] == f'{tx_kind}_deposit':
                asset = row['Currency']
                investments_deposits[asset].append(row)
            elif row['Transaction Kind'] == f'{tx_kind}_withdrawal':
                asset = row['Currency']
                investments_withdrawals[asset].append(row)

        for timestamp, m_row in multiple_rows.items():
            # When we convert multiple assets dust to CRO
            # in one time, it will create multiple debited rows with
            # the same timestamp
            debited_rows = []
            try:
                debited_rows = m_row['debited']
                credited_row = m_row['credited']
            except KeyError as e:
                for row in debited_rows + [credited_row]:
                    if row:
                        self.send_message(
                            row_index=row[INDEX],
                            csv_row=row,
                            msg=f'Failed to get {e!s} event at timestamp {timestamp}.',
                            is_error=True,
                        )

                continue

            total_debited_usd = functools.reduce(
                lambda acc, row:
                    acc +
                    deserialize_fval(row['Native Amount (in USD)']),
                debited_rows,
                ZERO,
            )

            # If the value of the transaction is too small (< 0,01$),
            # crypto.com will display 0 as native amount
            # if we have multiple debited rows, we can't import them
            # since we can't compute their dedicated rates, so we skip them
            if len(debited_rows) > 1 and total_debited_usd == 0:
                for row in debited_rows:
                    self.send_message(
                        row_index=row[INDEX],
                        csv_row=row,
                        msg="Can't import multiple debited rows with value of 0.",
                        is_error=True,
                    )
                return

            if credited_row is not None and len(debited_rows) != 0:
                for debited_row in debited_rows:
                    description = credited_row['Transaction Description']
                    notes = f'{description}\nSource: crypto.com (CSV import)'
                    # No fees here
                    fee = Fee(ZERO)
                    fee_currency = A_USD

                    base_asset = asset_from_cryptocom(credited_row['Currency'])
                    quote_asset = asset_from_cryptocom(debited_row['Currency'])
                    part_of_total = (
                        ONE
                        if len(debited_rows) == 1
                        else deserialize_fval(
                            debited_row['Native Amount (in USD)'],
                        ) / total_debited_usd
                    )
                    quote_amount_sold = deserialize_fval(
                        debited_row['Amount'],
                    ) * part_of_total
                    base_amount_bought = deserialize_fval(
                        credited_row['Amount'],
                    ) * part_of_total

                    self.add_history_events(
                        write_cursor=write_cursor,
                        history_events=create_swap_events(
                            event_identifier=f'{CRYPTOCOM_PREFIX}{hash_csv_row_without_index(debited_row)}',
                            timestamp=ts_sec_to_ms(timestamp),
                            spend=AssetAmount(asset=quote_asset, amount=abs(quote_amount_sold)),
                            receive=AssetAmount(asset=base_asset, amount=abs(base_amount_bought)),
                            fee=AssetAmount(asset=fee_currency, amount=fee),
                            location=Location.CRYPTOCOM,
                            spend_notes=notes,
                        ),
                    )

                # Add total number of rows associated with trade (1 credited_row and 1 or more debited_rows)  # noqa: E501
                self.imported_entries += 1 + len(debited_rows)

        # Compute investments profit
        if len(investments_withdrawals) != 0:
            for asset, withdrawals in investments_withdrawals.items():
                asset_object = asset_from_cryptocom(asset)
                if asset not in investments_deposits:
                    log.error(
                        f'Investment withdrawal without deposit at crypto.com. Ignoring '
                        f'staking info for asset {asset_object}',
                    )
                    continue
                # Sort by date in ascending order
                withdrawals_rows = sorted(
                    withdrawals,
                    key=lambda x: deserialize_timestamp_from_date(
                        date=x['Timestamp (UTC)'],
                        formatstr=timestamp_format,
                        location='cryptocom',
                    ),
                )
                investments_rows = sorted(
                    investments_deposits[asset],
                    key=lambda x: deserialize_timestamp_from_date(
                        date=x['Timestamp (UTC)'],
                        formatstr=timestamp_format,
                        location='cryptocom',
                    ),
                )
                last_date = Timestamp(0)
                for withdrawal in withdrawals_rows:
                    withdrawal_date = deserialize_timestamp_from_date(
                        date=withdrawal['Timestamp (UTC)'],
                        formatstr=timestamp_format,
                        location='cryptocom',
                    )
                    amount_deposited = ZERO
                    for deposit in investments_rows:
                        deposit_date = deserialize_timestamp_from_date(
                            date=deposit['Timestamp (UTC)'],
                            formatstr=timestamp_format,
                            location='cryptocom',
                        )
                        if last_date < deposit_date <= withdrawal_date:
                            # Amount is negative
                            amount_deposited += deserialize_fval(deposit['Amount'])
                    amount_withdrawal = deserialize_fval(withdrawal['Amount'])
                    # Compute profit
                    profit = amount_withdrawal + amount_deposited
                    if profit >= ZERO:
                        last_date = withdrawal_date
                        event = HistoryEvent(
                            event_identifier=f'{CRYPTOCOM_PREFIX}{hash_csv_row_without_index(withdrawal)}',
                            sequence_index=0,
                            timestamp=ts_sec_to_ms(withdrawal_date),
                            location=Location.CRYPTOCOM,
                            event_type=HistoryEventType.RECEIVE,
                            event_subtype=HistoryEventSubType.NONE,
                            amount=profit,
                            asset=asset_object,
                            notes=f'Staking profit for {asset}',
                        )
                        self.add_history_events(write_cursor, [event])

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            try:
                #  Notice: Crypto.com csv export gathers all swapping entries (`lockup_swap_*`,
                # `crypto_wallet_swap_*`, ...) into one entry named `dynamic_coin_swap_*`.
                self._import_cryptocom_associated_entries(
                    write_cursor=write_cursor,
                    data=data,
                    tx_kind='dynamic_coin_swap',
                    **kwargs,
                )
                # reset the iterator
                csvfile.seek(0)
                # pass the header since seek(0) make the first row to be the header
                next(data)

                self._import_cryptocom_associated_entries(
                    write_cursor=write_cursor,
                    data=data,
                    tx_kind='dust_conversion',
                    **kwargs,
                )
                csvfile.seek(0)
                next(data)

                self._import_cryptocom_associated_entries(write_cursor, data, 'interest_swap', **kwargs)  # noqa: E501
                csvfile.seek(0)
                next(data)

                self._import_cryptocom_associated_entries(write_cursor, data, 'invest', **kwargs)
                csvfile.seek(0)
                next(data)
            except KeyError as e:
                raise InputError(f'Crypto.com csv missing entry for {e!s}') from e
            except UnknownAsset as e:
                raise InputError(f'Encountered unknown asset {e!s} at crypto.com csv import') from e  # noqa: E501

            for index, row in enumerate(data, start=1):
                try:
                    self.total_entries += 1
                    self._consume_cryptocom_entry(write_cursor, row, **kwargs)
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
                except SkippedCSVEntry as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=str(e),
                        is_error=False,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
