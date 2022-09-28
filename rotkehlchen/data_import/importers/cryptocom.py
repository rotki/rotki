import csv
import functools
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.assets.converters import asset_from_cryptocom
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CryptocomImporter(BaseExchangeImporter):
    def _consume_cryptocom_entry(
            self,
            cursor: DBCursor,
            csv_row: Dict[str, Any],
            timestamp_format: str = '%Y-%m-%d %H:%M:%S',
    ) -> None:
        """Consumes a cryptocom entry row from the CSV and adds it into the database
        Can raise:
            - DeserializationError if something is wrong with the format of the expected values
            - UnsupportedCryptocomEntry if importing of this entry is not supported.
            - KeyError if the an expected CSV key is missing
            - UnknownAsset if one of the assets founds in the entry are not supported
        """
        row_type = csv_row['Transaction Kind']
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Timestamp (UTC)'],
            formatstr=timestamp_format,
            location='cryptocom',
        )
        description = csv_row['Transaction Description']
        notes = f'{description}\nSource: crypto.com (CSV import)'

        # No fees info until (Nov 2020) on crypto.com
        # fees are not displayed in the export data
        fee = Fee(ZERO)
        fee_currency = A_USD  # whatever (used only if there is no fee)

        if row_type in (
            'crypto_purchase',
            'crypto_exchange',
            'card_cashback_reverted',
            'viban_purchase',
            'crypto_viban_exchange',
            'recurring_buy_order',
            'card_top_up',
        ):
            # variable mapping to raw data
            currency = csv_row['Currency']
            to_currency = csv_row['To Currency']
            native_currency = csv_row['Native Currency']
            amount = csv_row['Amount']
            to_amount = csv_row['To Amount']
            native_amount = csv_row['Native Amount']

            trade_type = TradeType.BUY if to_currency != native_currency else TradeType.SELL

            if row_type in (
                'crypto_exchange',
                'crypto_viban_exchange',
                'recurring_buy_order',
                'viban_purchase',
            ):
                # trades (fiat, crypto) to (crypto, fiat)
                base_asset = asset_from_cryptocom(to_currency)
                quote_asset = asset_from_cryptocom(currency)
                if quote_asset is None:
                    raise DeserializationError('Got a trade entry with an empty quote asset')
                base_amount_bought = deserialize_asset_amount(to_amount)
                quote_amount_sold = deserialize_asset_amount(amount)
            elif row_type == 'card_top_up':
                quote_asset = asset_from_cryptocom(currency)
                base_asset = asset_from_cryptocom(native_currency)
                base_amount_bought = deserialize_asset_amount_force_positive(native_amount)
                quote_amount_sold = deserialize_asset_amount_force_positive(amount)
            else:
                base_asset = asset_from_cryptocom(currency)
                quote_asset = asset_from_cryptocom(native_currency)
                base_amount_bought = deserialize_asset_amount(amount)
                quote_amount_sold = deserialize_asset_amount(native_amount)

            rate = Price(abs(quote_amount_sold / base_amount_bought))
            trade = Trade(
                timestamp=timestamp,
                location=Location.CRYPTOCOM,
                base_asset=base_asset,
                quote_asset=quote_asset,
                trade_type=trade_type,
                amount=base_amount_bought,
                rate=rate,
                fee=fee,
                fee_currency=fee_currency,
                link='',
                notes=notes,
            )
            self.add_trade(cursor, trade)

        elif row_type in (
            'crypto_withdrawal',
            'crypto_deposit',
            'viban_deposit',
            'viban_card_top_up',
        ):
            if row_type in ('crypto_withdrawal', 'viban_deposit', 'viban_card_top_up'):
                category = AssetMovementCategory.WITHDRAWAL
                amount = deserialize_asset_amount_force_positive(csv_row['Amount'])
            else:
                category = AssetMovementCategory.DEPOSIT
                amount = deserialize_asset_amount(csv_row['Amount'])

            asset = asset_from_cryptocom(csv_row['Currency'])
            asset_movement = AssetMovement(
                location=Location.CRYPTOCOM,
                category=category,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=fee,
                fee_asset=asset,
                link='',
            )
            self.add_asset_movement(cursor, asset_movement)
        elif row_type in (
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
        ):
            asset = asset_from_cryptocom(csv_row['Currency'])
            amount = deserialize_asset_amount(csv_row['Amount'])
            action = LedgerAction(
                identifier=0,  # whatever is not used at insertion
                timestamp=timestamp,
                action_type=LedgerActionType.INCOME,
                location=Location.CRYPTOCOM,
                amount=amount,
                asset=asset,
                rate=None,
                rate_asset=None,
                link=None,
                notes=notes,
            )
            self.add_ledger_action(cursor, action)
        elif row_type in ('crypto_payment', 'reimbursement_reverted'):
            asset = asset_from_cryptocom(csv_row['Currency'])
            amount = abs(deserialize_asset_amount(csv_row['Amount']))
            action = LedgerAction(
                identifier=0,  # whatever is not used at insertion
                timestamp=timestamp,
                action_type=LedgerActionType.EXPENSE,
                location=Location.CRYPTOCOM,
                amount=amount,
                asset=asset,
                rate=None,
                rate_asset=None,
                link=None,
                notes=notes,
            )
            self.add_ledger_action(cursor, action)
        elif row_type == 'invest_deposit':
            asset = asset_from_cryptocom(csv_row['Currency'])
            amount = deserialize_asset_amount(csv_row['Amount'])
            asset_movement = AssetMovement(
                location=Location.CRYPTOCOM,
                category=AssetMovementCategory.DEPOSIT,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=fee,
                fee_asset=fee_currency,
                link='',
            )
            self.add_asset_movement(cursor, asset_movement)
        elif row_type == 'invest_withdrawal':
            asset = asset_from_cryptocom(csv_row['Currency'])
            amount = deserialize_asset_amount(csv_row['Amount'])
            asset_movement = AssetMovement(
                location=Location.CRYPTOCOM,
                category=AssetMovementCategory.WITHDRAWAL,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=fee,
                fee_asset=fee_currency,
                link='',
            )
            self.add_asset_movement(cursor, asset_movement)
        elif row_type == 'crypto_transfer':
            asset = asset_from_cryptocom(csv_row['Currency'])
            amount = deserialize_asset_amount(csv_row['Amount'])
            if amount < 0:
                action_type = LedgerActionType.EXPENSE
                amount = abs(amount)
            else:
                action_type = LedgerActionType.INCOME
            action = LedgerAction(
                identifier=0,  # whatever is not used at insertion
                timestamp=timestamp,
                action_type=action_type,
                location=Location.CRYPTOCOM,
                amount=amount,
                asset=asset,
                rate=None,
                rate_asset=None,
                link=None,
                notes=notes,
            )
            self.add_ledger_action(cursor, action)
        elif row_type in (
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
            'dynamic_coin_swap_bonus_exchange_deposit',
            # we don't handle cryto.com exchange yet
            'crypto_to_exchange_transfer',
            'exchange_to_crypto_transfer',
            # supercharger actions
            'supercharger_deposit',
            'supercharger_withdrawal',
            # already handled using _import_cryptocom_associated_entries
            'dynamic_coin_swap_debited',
            'dynamic_coin_swap_credited',
            'dust_conversion_debited',
            'dust_conversion_credited',
            'interest_swap_credited',
            'interest_swap_debited',
            # The user has received an aidrop but can't claim it yet
            'airdrop_locked',
        ):
            # those types are ignored because it doesn't affect the wallet balance
            # or are not handled here
            return
        else:
            raise UnsupportedCSVEntry(
                f'Unknown entrype type "{row_type}" encountered during '
                f'cryptocom data import. Ignoring entry',
            )

    def _import_cryptocom_associated_entries(
        self,
        cursor: DBCursor,
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
        multiple_rows: Dict[Any, Dict[str, Any]] = {}
        investments_deposits: Dict[str, List[Any]] = defaultdict(list)
        investments_withdrawals: Dict[str, List[Any]] = defaultdict(list)
        debited_row = None
        credited_row = None
        expects_debited = False
        credited_timestamp = None
        for row in data:
            log.debug(f'Processing cryptocom row at {row["Timestamp (UTC)"]} and type {tx_kind}')
            # If we don't have the corresponding debited entry ignore them
            # and warn the user
            if (
                expects_debited is True and
                row['Transaction Kind'] != f'{tx_kind}_debited'
            ):
                self.db.msg_aggregator.add_warning(
                    f'Error during cryptocom CSV import consumption. Found {tx_kind}_credited '
                    f'but no amount debited afterwards at date {row["Timestamp (UTC)"]}',
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
                    self.db.msg_aggregator.add_warning(
                        f'Error during cryptocom CSV import consumption. Found {tx_kind}_debited'
                        f' but no amount credited before at date {row["Timestamp (UTC)"]}',
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

        for timestamp in multiple_rows:
            # When we convert multiple assets dust to CRO
            # in one time, it will create multiple debited rows with
            # the same timestamp
            try:
                debited_rows = multiple_rows[timestamp]['debited']
                credited_row = multiple_rows[timestamp]['credited']
            except KeyError as e:
                self.db.msg_aggregator.add_warning(
                    f'Failed to get {str(e)} event at timestamp {timestamp}.',
                )
                continue
            total_debited_usd = functools.reduce(
                lambda acc, row:
                    acc +
                    deserialize_asset_amount(row['Native Amount (in USD)']),
                debited_rows,
                ZERO,
            )

            # If the value of the transaction is too small (< 0,01$),
            # crypto.com will display 0 as native amount
            # if we have multiple debited rows, we can't import them
            # since we can't compute their dedicated rates, so we skip them
            if len(debited_rows) > 1 and total_debited_usd == 0:
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
                        else deserialize_asset_amount(
                            debited_row["Native Amount (in USD)"],
                        ) / total_debited_usd
                    )
                    quote_amount_sold = deserialize_asset_amount(
                        debited_row['Amount'],
                    ) * part_of_total
                    base_amount_bought = deserialize_asset_amount(
                        credited_row['Amount'],
                    ) * part_of_total

                    if base_amount_bought != ZERO:
                        rate = Price(abs(quote_amount_sold / base_amount_bought))
                    else:
                        rate = Price(ZERO)

                    trade = Trade(
                        timestamp=timestamp,
                        location=Location.CRYPTOCOM,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        trade_type=TradeType.BUY,
                        amount=AssetAmount(base_amount_bought),
                        rate=rate,
                        fee=fee,
                        fee_currency=fee_currency,
                        link='',
                        notes=notes,
                    )
                    self.add_trade(cursor, trade)

        # Compute investments profit
        if len(investments_withdrawals) != 0:
            for asset in investments_withdrawals:
                asset_object = asset_from_cryptocom(asset)
                if asset not in investments_deposits:
                    log.error(
                        f'Investment withdrawal without deposit at crypto.com. Ignoring '
                        f'staking info for asset {asset_object}',
                    )
                    continue
                # Sort by date in ascending order
                withdrawals_rows = sorted(
                    investments_withdrawals[asset],
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
                            amount_deposited += deserialize_asset_amount(deposit['Amount'])
                    amount_withdrawal = deserialize_asset_amount(withdrawal['Amount'])
                    # Compute profit
                    profit = amount_withdrawal + amount_deposited
                    if profit >= ZERO:
                        last_date = withdrawal_date
                        action = LedgerAction(
                            identifier=0,  # whatever is not used at insertion
                            timestamp=withdrawal_date,
                            action_type=LedgerActionType.INCOME,
                            location=Location.CRYPTOCOM,
                            amount=AssetAmount(profit),
                            asset=asset_object,
                            rate=None,
                            rate_asset=None,
                            link=None,
                            notes=f'Stake profit for asset {asset}',
                        )
                        self.add_ledger_action(cursor, action)

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            try:
                #  Notice: Crypto.com csv export gathers all swapping entries (`lockup_swap_*`,
                # `crypto_wallet_swap_*`, ...) into one entry named `dynamic_coin_swap_*`.
                self._import_cryptocom_associated_entries(
                    cursor=cursor,
                    data=data,
                    tx_kind='dynamic_coin_swap',
                    **kwargs,
                )
                # reset the iterator
                csvfile.seek(0)
                # pass the header since seek(0) make the first row to be the header
                next(data)

                self._import_cryptocom_associated_entries(
                    cursor=cursor,
                    data=data,
                    tx_kind='dust_conversion',
                    **kwargs,
                )
                csvfile.seek(0)
                next(data)

                self._import_cryptocom_associated_entries(cursor, data, 'interest_swap', **kwargs)
                csvfile.seek(0)
                next(data)

                self._import_cryptocom_associated_entries(cursor, data, 'invest', **kwargs)
                csvfile.seek(0)
                next(data)
            except KeyError as e:
                raise InputError(f'Crypto.com csv missing entry for {str(e)}') from e
            except UnknownAsset as e:
                raise InputError(f'Encountered unknown asset {str(e)} at crypto.com csv import') from e  # noqa: E501

            for row in data:
                try:
                    self._consume_cryptocom_entry(cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During cryptocom CSV import found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Error during cryptocom CSV import deserialization. '
                        f'Error was {str(e)}. Ignoring entry',
                    )
                    continue
                except UnsupportedCSVEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                    continue
                except KeyError as e:
                    raise InputError(f'Could not find key {str(e)} in csv row {str(row)}') from e
