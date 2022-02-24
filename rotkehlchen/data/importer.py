import csv
import functools
import logging
from collections import defaultdict
from itertools import count
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.assets.converters import asset_from_cryptocom, asset_from_nexo, asset_from_uphold
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants.assets import A_BSQ, A_BTC, A_DAI, A_SAI, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, AssetMovementCategory, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.typing import AssetAmount, Fee, Location, Price, Timestamp, TradeType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SAI_TIMESTAMP = 1574035200


def remap_header(fieldnames: List[str]) -> List[str]:
    cur_count = count(1)
    mapping = {1: 'Buy', 2: 'Sell', 3: 'Fee'}
    return [f'Cur.{mapping[next(cur_count)]}' if f.startswith('Cur.') else f for f in fieldnames]


class UnsupportedCSVEntry(Exception):
    """Thrown for external exchange exported entries we can't import"""


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
    if entry in ('CoinbasePro', 'GDAX'):
        return Location.COINBASEPRO
    # TODO: Check if this is the correct string for Gemini from cointracking
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


class DataImporter():

    def __init__(self, db: DBHandler) -> None:
        self.db = db
        self.db_ledger = DBLedgerActions(self.db, self.db.msg_aggregator)

    def _consume_cointracking_entry(self, csv_row: Dict[str, Any], **kwargs: Any) -> None:
        """Consumes a cointracking entry row from the CSV and adds it into the database
        Can raise:
            - DeserializationError if something is wrong with the format of the expected values
            - UnsupportedCSVEntry if importing of this entry is not supported.
            - IndexError if the CSV file is corrupt
            - KeyError if the an expected CSV key is missing
            - UnknownAsset if one of the assets founds in the entry are not supported
        """
        row_type = csv_row['Type']
        formatstr = kwargs.get('timestamp_format')
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr=formatstr if formatstr is not None else '%d.%m.%Y %H:%M:%S',
            location='cointracking.info',
        )
        location = exchange_row_to_location(csv_row['Exchange'])
        notes = csv_row['Comment']
        if location == Location.EXTERNAL:
            notes += f'. Data from -{csv_row["Exchange"]}- not known by rotki.'

        fee = Fee(ZERO)
        fee_currency = A_USD  # whatever (used only if there is no fee)
        if csv_row['Fee'] != '':
            fee = deserialize_fee(csv_row['Fee'])
            fee_currency = asset_from_cryptocom(csv_row['Cur.Fee'])

        if row_type in ('Gift/Tip', 'Trade', 'Income'):
            base_asset = asset_from_cryptocom(csv_row['Cur.Buy'])
            quote_asset = None if csv_row['Cur.Sell'] == '' else asset_from_cryptocom(csv_row['Cur.Sell'])  # noqa: E501
            if quote_asset is None and row_type not in ('Gift/Tip', 'Income'):
                raise DeserializationError('Got a trade entry with an empty quote asset')

            if quote_asset is None:
                # Really makes no difference as this is just a gift and the amount is zero
                quote_asset = A_USD
            base_amount_bought = deserialize_asset_amount(csv_row['Buy'])
            if csv_row['Sell'] != '-':
                quote_amount_sold = deserialize_asset_amount(csv_row['Sell'])
            else:
                quote_amount_sold = AssetAmount(ZERO)
            rate = Price(quote_amount_sold / base_amount_bought)

            trade = Trade(
                timestamp=timestamp,
                location=location,
                base_asset=base_asset,
                quote_asset=quote_asset,
                trade_type=TradeType.BUY,  # It's always a buy during cointracking import
                amount=base_amount_bought,
                rate=rate,
                fee=fee,
                fee_currency=fee_currency,
                link='',
                notes=notes,
            )
            self.db.add_trades([trade])
        elif row_type in ('Deposit', 'Withdrawal'):
            category = deserialize_asset_movement_category(row_type.lower())
            if category == AssetMovementCategory.DEPOSIT:
                amount = deserialize_asset_amount(csv_row['Buy'])
                asset = asset_from_cryptocom(csv_row['Cur.Buy'])
            else:
                amount = deserialize_asset_amount_force_positive(csv_row['Sell'])
                asset = asset_from_cryptocom(csv_row['Cur.Sell'])

            asset_movement = AssetMovement(
                location=location,
                category=category,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=fee,
                fee_asset=fee_currency,
                link='',
            )
            self.db.add_asset_movements([asset_movement])
        else:
            raise UnsupportedCSVEntry(
                f'Unknown entrype type "{row_type}" encountered during cointracking '
                f'data import. Ignoring entry',
            )

    def import_cointracking_csv(
        self,
        filepath: Path,
        **kwargs: Any,
    ) -> Tuple[bool, str]:
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.reader(csvfile, delimiter=',', quotechar='"')
            header = remap_header(next(data))
            for row in data:
                try:
                    self._consume_cointracking_entry(dict(zip(header, row)), **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During cointracking CSV import found action with unknown '
                        f'asset {e.asset_name}. Ignoring entry',
                    )
                    continue
                except IndexError:
                    self.db.msg_aggregator.add_warning(
                        'During cointracking CSV import found entry with '
                        'unexpected number of columns',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Error during cointracking CSV import deserialization. '
                        f'Error was {str(e)}. Ignoring entry',
                    )
                    continue
                except UnsupportedCSVEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                    continue
                except KeyError as e:
                    return False, str(e)
        return True, ''

    def _consume_cryptocom_entry(self, csv_row: Dict[str, Any], **kwargs: Any) -> None:
        """Consumes a cryptocom entry row from the CSV and adds it into the database
        Can raise:
            - DeserializationError if something is wrong with the format of the expected values
            - UnsupportedCryptocomEntry if importing of this entry is not supported.
            - KeyError if the an expected CSV key is missing
            - UnknownAsset if one of the assets founds in the entry are not supported
            - sqlcipher.IntegrityError from db_ledger.add_ledger_action
        """
        row_type = csv_row['Transaction Kind']
        formatstr = kwargs.get('timestamp_format')
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Timestamp (UTC)'],
            formatstr=formatstr if formatstr is not None else '%Y-%m-%d %H:%M:%S',
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
            'reimbursement',
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
            self.db.add_trades([trade])

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
            self.db.add_asset_movements([asset_movement])
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
            self.db_ledger.add_ledger_action(action)
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
            self.db_ledger.add_ledger_action(action)
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
            self.db.add_asset_movements([asset_movement])
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
            self.db.add_asset_movements([asset_movement])
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
            self.db_ledger.add_ledger_action(action)
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
        data: Any,
        tx_kind: str,
        **kwargs: Any,
    ) -> None:
        """Look for events that have associated entries and handle them as trades.

        This method looks for `*_debited` and `*_credited` entries using the
        same timestamp to handle them as one trade.

        Known kind: 'dynamic_coin_swap' or 'dust_conversion'

        May raise:
        - UnknownAsset if an unknown asset is encountered in the imported files
        - KeyError if a row contains unexpected data entries
        - sqlcipher.IntegrityError from db_ledger.add_ledger_action
        """
        multiple_rows: Dict[Any, Dict[str, Any]] = {}
        investments_deposits: Dict[str, List[Any]] = defaultdict(list)
        investments_withdrawals: Dict[str, List[Any]] = defaultdict(list)
        debited_row = None
        credited_row = None
        expects_debited = False
        credited_timestamp = None
        formatstr = kwargs.get('timestamp_format')
        timestamp_format = formatstr if formatstr is not None else '%Y-%m-%d %H:%M:%S'
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
                # They only is one credited row
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
                        FVal(1)
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
                    self.db.add_trades([trade])

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
                        self.db_ledger.add_ledger_action(action)

    def import_cryptocom_csv(self, filepath: Path, **kwargs: Any) -> Tuple[bool, str]:
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            try:
                #  Notice: Crypto.com csv export gathers all swapping entries (`lockup_swap_*`,
                # `crypto_wallet_swap_*`, ...) into one entry named `dynamic_coin_swap_*`.
                self._import_cryptocom_associated_entries(
                    data=data,
                    tx_kind='dynamic_coin_swap',
                    **kwargs,
                )
                # reset the iterator
                csvfile.seek(0)
                # pass the header since seek(0) make the first row to be the header
                next(data)

                self._import_cryptocom_associated_entries(
                    data=data,
                    tx_kind='dust_conversion',
                    **kwargs,
                )
                csvfile.seek(0)
                next(data)

                self._import_cryptocom_associated_entries(data, 'interest_swap', **kwargs)
                csvfile.seek(0)
                next(data)

                self._import_cryptocom_associated_entries(data, 'invest', **kwargs)
                csvfile.seek(0)
                next(data)
            except KeyError as e:
                return False, f'Crypto.com csv missing entry for {str(e)}'
            except UnknownAsset as e:
                return False, f'Encountered unknown asset {str(e)} at crypto.com csv import'
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.db.conn.rollback()
                self.db.msg_aggregator.add_warning(
                    'Error during cryptocom CSV import consumption. '
                    ' Entry already existed in DB. Ignoring.',
                )
                # continue, since they already are in DB

            for row in data:
                try:
                    self._consume_cryptocom_entry(row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During cryptocom CSV import found action with unknown '
                        f'asset {e.asset_name}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Error during cryptocom CSV import deserialization. '
                        f'Error was {str(e)}. Ignoring entry',
                    )
                    continue
                except sqlcipher.IntegrityError:  # pylint: disable=no-member
                    self.db.conn.rollback()
                    self.db.msg_aggregator.add_warning(
                        'Error during cryptocom CSV import consumption. '
                        ' Entry already existed in DB. Ignoring.',
                    )
                    log.warning(f'cryptocom csv entry {row} aleady existed in DB')
                    continue
                except UnsupportedCSVEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                    continue
                except KeyError as e:
                    return False, str(e)
        return True, ''

    def _consume_blockfi_entry(self, csv_row: Dict[str, Any], **kwargs: Any) -> None:
        """
        Process entry for BlockFi transaction history. Trades for this file are ignored
        and istead should be extracted from the file containing only trades.
        This method can raise:
        - UnsupportedBlockFiEntry
        - UnknownAsset
        - DeserializationError
        - sqlcipher.IntegrityError from db_ledger.add_ledger_action
        """
        if len(csv_row['Confirmed At']) != 0:
            formatstr = kwargs.get('timestamp_format')
            timestamp = deserialize_timestamp_from_date(
                date=csv_row['Confirmed At'],
                formatstr=formatstr if formatstr is not None else '%Y-%m-%d %H:%M:%S',
                location='BlockFi',
            )
        else:
            log.debug(f'Ignoring unconfirmed BlockFi entry {csv_row}')
            return

        asset = symbol_to_asset_or_token(csv_row['Cryptocurrency'])
        amount = deserialize_asset_amount_force_positive(csv_row['Amount'])
        entry_type = csv_row['Transaction Type']
        # BlockFI doesn't provide information about fees
        fee = Fee(ZERO)
        fee_asset = A_USD  # Can be whatever

        if entry_type in ('Deposit', 'Wire Deposit', 'ACH Deposit'):
            asset_movement = AssetMovement(
                location=Location.BLOCKFI,
                category=AssetMovementCategory.DEPOSIT,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=fee,
                fee_asset=fee_asset,
                link='',
            )
            self.db.add_asset_movements([asset_movement])
        elif entry_type in ('Withdrawal', 'Wire Withdrawal', 'ACH Withdrawal'):
            asset_movement = AssetMovement(
                location=Location.BLOCKFI,
                category=AssetMovementCategory.WITHDRAWAL,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=fee,
                fee_asset=fee_asset,
                link='',
            )
            self.db.add_asset_movements([asset_movement])
        elif entry_type == 'Withdrawal Fee':
            action = LedgerAction(
                identifier=0,  # whatever is not used at insertion
                timestamp=timestamp,
                action_type=LedgerActionType.EXPENSE,
                location=Location.BLOCKFI,
                amount=amount,
                asset=asset,
                rate=None,
                rate_asset=None,
                link=None,
                notes=f'{entry_type} from BlockFi',
            )
            self.db_ledger.add_ledger_action(action)
        elif entry_type in ('Interest Payment', 'Bonus Payment', 'Referral Bonus'):
            action = LedgerAction(
                identifier=0,  # whatever is not used at insertion
                timestamp=timestamp,
                action_type=LedgerActionType.INCOME,
                location=Location.BLOCKFI,
                amount=amount,
                asset=asset,
                rate=None,
                rate_asset=None,
                link=None,
                notes=f'{entry_type} from BlockFi',
            )
            self.db_ledger.add_ledger_action(action)
        elif entry_type == 'Trade':
            pass
        else:
            raise UnsupportedCSVEntry(f'Unsuported entry {entry_type}. Data: {csv_row}')

    def import_blockfi_transactions_csv(self, filepath: Path, **kwargs: Any) -> Tuple[bool, str]:
        """
        Information for the values that the columns can have has been obtained from
        https://github.com/BittyTax/BittyTax/blob/06794f51223398759852d6853bc7112ffb96129a/bittytax/conv/parsers/blockfi.py#L67
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_blockfi_entry(row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During BlockFi CSV import found action with unknown '
                        f'asset {e.asset_name}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during BlockFi CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except sqlcipher.IntegrityError:  # pylint: disable=no-member
                    self.db.conn.rollback()
                    self.db.msg_aggregator.add_warning(
                        'Error during blockfi CSV import consumption. '
                        ' Entry already existed in DB. Ignoring.',
                    )
                    log.warning(f'blocki csv entry {row} aleady existed in DB')
                    continue
                except UnsupportedCSVEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                    continue
                except KeyError as e:
                    return False, str(e)
        return True, ''

    def _consume_blockfi_trade(self, csv_row: Dict[str, Any], **kwargs: Any) -> None:
        """
        Consume the file containing only trades from BlockFi. As per my investigations
        (@yabirgb) this file can only contain confirmed trades.
        - UnknownAsset
        - DeserializationError
        """
        formatstr = kwargs.get('timestamp_format')
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr=formatstr if formatstr is not None else '%Y-%m-%d %H:%M:%S',
            location='BlockFi',
        )

        buy_asset = symbol_to_asset_or_token(csv_row['Buy Currency'])
        buy_amount = deserialize_asset_amount(csv_row['Buy Quantity'])
        sold_asset = symbol_to_asset_or_token(csv_row['Sold Currency'])
        sold_amount = deserialize_asset_amount(csv_row['Sold Quantity'])
        if sold_amount == ZERO:
            log.debug(f'Ignoring BlockFi trade with sold_amount equal to zero. {csv_row}')
            return
        rate = Price(buy_amount / sold_amount)
        trade = Trade(
            timestamp=timestamp,
            location=Location.BLOCKFI,
            base_asset=sold_asset,
            quote_asset=buy_asset,
            trade_type=TradeType.SELL,
            amount=sold_amount,
            rate=rate,
            fee=None,  # BlockFI doesn't provide this information
            fee_currency=None,
            link='',
            notes=csv_row['Type'],
        )
        self.db.add_trades([trade])

    def import_blockfi_trades_csv(self, filepath: Path, **kwargs: Any) -> Tuple[bool, str]:
        """
        Information for the values that the columns can have has been obtained from
        the issue in github #1674
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_blockfi_trade(row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During BlockFi CSV import found action with unknown '
                        f'asset {e.asset_name}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during BlockFi CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except KeyError as e:
                    return False, str(e)
        return True, ''

    def _consume_nexo(self, csv_row: Dict[str, Any], **kwargs: Any) -> None:
        """
        Consume CSV file from NEXO.
        This method can raise:
        - UnsupportedNexoEntry
        - UnknownAsset
        - DeserializationError
        - sqlcipher.IntegrityError from db_ledger.add_ledger_action
        """
        ignored_entries = (
            'ExchangeToWithdraw',
            'DepositToExchange',
            'UnlockingTermDeposit',  # Move between nexo wallets
            'LockingTermDeposit',  # Move between nexo wallets
            'TransferIn',  # Transfer between nexo wallets
            'TransferOut',  # Transfer between nexo wallets
        )

        if 'rejected' not in csv_row['Details']:
            formatstr = kwargs.get('timestamp_format')
            timestamp = deserialize_timestamp_from_date(
                date=csv_row['Date / Time'],
                formatstr=formatstr if formatstr is not None else '%Y-%m-%d %H:%M:%S',
                location='NEXO',
            )
        else:
            log.debug(f'Ignoring rejected nexo entry {csv_row}')
            return

        asset = asset_from_nexo(csv_row['Currency'])
        amount = deserialize_asset_amount_force_positive(csv_row['Amount'])
        entry_type = csv_row['Type']
        transaction = csv_row['Transaction']

        if entry_type == 'Exchange':
            self.db.msg_aggregator.add_warning(
                'Found exchange transaction in nexo csv import but the entry will be ignored '
                'since not enough information is provided about the trade.',
            )
            return
        if entry_type in ('Deposit', 'ExchangeDepositedOn'):
            asset_movement = AssetMovement(
                location=Location.NEXO,
                category=AssetMovementCategory.DEPOSIT,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=Fee(ZERO),
                fee_asset=A_USD,
                link=transaction,
            )
            self.db.add_asset_movements([asset_movement])
        elif entry_type in ('Withdrawal', 'WithdrawExchanged'):
            asset_movement = AssetMovement(
                location=Location.NEXO,
                category=AssetMovementCategory.WITHDRAWAL,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=Fee(ZERO),
                fee_asset=A_USD,
                link=transaction,
            )
            self.db.add_asset_movements([asset_movement])
        elif entry_type == 'Withdrawal Fee':
            action = LedgerAction(
                identifier=0,  # whatever is not used at insertion
                timestamp=timestamp,
                action_type=LedgerActionType.EXPENSE,
                location=Location.NEXO,
                amount=amount,
                asset=asset,
                rate=None,
                rate_asset=None,
                link=None,
                notes=f'{entry_type} from Nexo',
            )
            self.db_ledger.add_ledger_action(action)
        elif entry_type in ('Interest', 'Bonus', 'Dividend', 'FixedTermInterest'):
            # A user shared a CSV file where some entries marked as interest had negative amounts.
            # we couldn't find information about this since they seem internal transactions made
            # by nexo but they appear like a trade from asset -> nexo in order to gain interest
            # in nexo. There seems to always be another entry with the amount that the user
            # received so we'll ignore interest rows with negative amounts.
            if deserialize_asset_amount(csv_row['Amount']) < 0:
                log.debug(f'Ignoring nexo entry {csv_row} with negative interest')
                return
            action = LedgerAction(
                identifier=0,  # whatever is not used at insertion
                timestamp=timestamp,
                action_type=LedgerActionType.INCOME,
                location=Location.NEXO,
                amount=amount,
                asset=asset,
                rate=None,
                rate_asset=None,
                link=transaction,
                notes=f'{entry_type} from Nexo',
            )
            self.db_ledger.add_ledger_action(action)
        elif entry_type in ignored_entries:
            pass
        else:
            raise UnsupportedCSVEntry(f'Unsuported entry {entry_type}. Data: {csv_row}')

    def import_nexo_csv(self, filepath: Path, **kwargs: Any) -> Tuple[bool, str]:
        """
        Information for the values that the columns can have has been obtained from
        https://github.com/BittyTax/BittyTax/blob/06794f51223398759852d6853bc7112ffb96129a/bittytax/conv/parsers/nexo.py
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_nexo(row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During Nexo CSV import found action with unknown '
                        f'asset {e.asset_name}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during Nexo CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except sqlcipher.IntegrityError:  # pylint: disable=no-member
                    self.db.conn.rollback()
                    self.db.msg_aggregator.add_warning(
                        'Error during nexro CSV import consumption. '
                        ' Entry already existed in DB. Ignoring.',
                    )
                    log.warning(f'nexo csv entry {row} aleady existed in DB')
                    continue
                except UnsupportedCSVEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                    continue
                except KeyError as e:
                    return False, str(e)
        return True, ''

    def _consume_shapeshift_trade(self, csv_row: Dict[str, Any], **kwargs: Any) -> None:
        """
        Consume the file containing only trades from ShapeShift.
        """
        formatstr = kwargs.get('timestamp_format')
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['timestamp'],
            formatstr=formatstr if formatstr is not None else 'iso8601',
            location='ShapeShift',
        )
        buy_asset = symbol_to_asset_or_token(csv_row['outputCurrency'])
        buy_amount = deserialize_asset_amount(csv_row['outputAmount'])
        sold_asset = symbol_to_asset_or_token(csv_row['inputCurrency'])
        sold_amount = deserialize_asset_amount(csv_row['inputAmount'])
        rate = deserialize_asset_amount(csv_row['rate'])
        fee = deserialize_fee(csv_row['minerFee'])
        gross_amount = AssetAmount(buy_amount + fee)
        in_addr = csv_row['inputAddress']
        out_addr = csv_row['outputAddress']
        notes = f"""
Trade from ShapeShift with ShapeShift Deposit Address:
 {csv_row['inputAddress']}, and
 Transaction ID: {csv_row['inputTxid']}.
  Refund Address: {csv_row['refundAddress']}, and
 Transaction ID: {csv_row['refundTxid']}.
  Destination Address: {csv_row['outputAddress']}, and
 Transaction ID: {csv_row['outputTxid']}.
"""
        if sold_amount == ZERO:
            log.debug(f'Ignoring ShapeShift trade with sold_amount equal to zero. {csv_row}')
            return
        if in_addr == '' or out_addr == '':
            log.debug(f'Ignoring ShapeShift trade which was performed on DEX. {csv_row}')
            return
        # Assuming that before launch of multi collateral dai everything was SAI.
        # Converting DAI to SAI in buy_asset and sell_asset.
        if buy_asset == A_DAI and timestamp <= SAI_TIMESTAMP:
            buy_asset = A_SAI
        if sold_asset == A_DAI and timestamp <= SAI_TIMESTAMP:
            sold_asset = A_SAI
        if rate <= ZERO:
            log.warning(f'shapeshift csv entry has negative or zero rate. Ignoring. {csv_row}')
            return

        # Fix the rate correctly (1 / rate) * (fee + buy_amount) = sell_amount
        trade = Trade(
            timestamp=timestamp,
            location=Location.SHAPESHIFT,
            base_asset=buy_asset,
            quote_asset=sold_asset,
            trade_type=TradeType.BUY,
            amount=gross_amount,
            rate=Price(1 / rate),
            fee=Fee(fee),
            fee_currency=buy_asset,  # Assumption that minerFee is denominated in outputCurrency
            link='',
            notes=notes,
        )
        self.db.add_trades([trade])

    def import_shapeshift_trades_csv(self, filepath: Path, **kwargs: Any) -> Tuple[bool, str]:
        """
        Information for the values that the columns can have has been obtained from sample CSVs
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_shapeshift_trade(row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During ShapeShift CSV import found action with unknown '
                        f'asset {e.asset_name}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during ShapeShift CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except KeyError as e:
                    return False, str(e)
        return True, ''

    def _consume_uphold_transaction(self, csv_row: Dict[str, Any], **kwargs: Any) -> None:
        """
        Consume the file containing both trades and transactions from uphold.
        This method can raise:
        - UnknownAsset
        - DeserializationError
        - KeyError
        """
        formatstr = kwargs.get('timestamp_format')
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr=formatstr if formatstr is not None else '%a %b %d %Y %H:%M:%S %Z%z',
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
                    action_type = LedgerActionType.INCOME
                elif transaction_type == 'out':
                    action_type = LedgerActionType.EXPENSE
                else:
                    log.debug(f'Ignoring uncaught transaction type of {transaction_type}.')
                    return
                action = LedgerAction(
                    identifier=0,
                    timestamp=timestamp,
                    action_type=action_type,
                    location=Location.UPHOLD,
                    amount=destination_amount,
                    asset=destination_asset,
                    rate=None,
                    rate_asset=None,
                    link='',
                    notes=notes,
                )
                self.db_ledger.add_ledger_action(action)
            else:  # Assets or amounts differ (Trades)
                # in uphold UI the exchanged amount includes the fee.
                if fee_asset == destination_asset:
                    destination_amount = AssetAmount(destination_amount + fee)
                if destination_amount > 0:
                    trade = Trade(
                        timestamp=timestamp,
                        location=Location.UPHOLD,
                        base_asset=destination_asset,
                        quote_asset=origin_asset,
                        trade_type=TradeType.BUY,
                        amount=destination_amount,
                        rate=Price(origin_amount / destination_amount),
                        fee=Fee(fee),
                        fee_currency=fee_asset,
                        link='',
                        notes=notes,
                    )
                    self.db.add_trades([trade])
                else:
                    log.debug(f'Ignoring trade with Destination Amount: {destination_amount}.')
        elif origin == 'uphold':
            if transaction_type == 'out':
                if origin_asset == destination_asset:  # Withdrawals
                    asset_movement = AssetMovement(
                        location=Location.UPHOLD,
                        category=AssetMovementCategory.WITHDRAWAL,
                        address=None,
                        transaction_id=None,
                        timestamp=timestamp,
                        asset=origin_asset,
                        amount=origin_amount,
                        fee=Fee(fee),
                        fee_asset=fee_asset,
                        link='',
                    )
                    self.db.add_asset_movements([asset_movement])
                else:  # Trades (sell)
                    if origin_amount > 0:
                        trade = Trade(
                            timestamp=timestamp,
                            location=Location.UPHOLD,
                            base_asset=origin_asset,
                            quote_asset=destination_asset,
                            trade_type=TradeType.SELL,
                            amount=origin_amount,
                            rate=Price(destination_amount / origin_amount),
                            fee=Fee(fee),
                            fee_currency=fee_asset,
                            link='',
                            notes=notes,
                        )
                        self.db.add_trades([trade])
                    else:
                        log.debug(f'Ignoring trade with Origin Amount: {origin_amount}.')
        elif destination == 'uphold':
            if transaction_type == 'in':
                if origin_asset == destination_asset:  # Deposits
                    asset_movement = AssetMovement(
                        location=Location.UPHOLD,
                        category=AssetMovementCategory.DEPOSIT,
                        address=None,
                        transaction_id=None,
                        timestamp=timestamp,
                        asset=origin_asset,
                        amount=origin_amount,
                        fee=Fee(fee),
                        fee_asset=fee_asset,
                        link='',
                    )
                    self.db.add_asset_movements([asset_movement])
                else:  # Trades (buy)
                    if destination_amount > 0:
                        trade = Trade(
                            timestamp=timestamp,
                            location=Location.UPHOLD,
                            base_asset=destination_asset,
                            quote_asset=origin_asset,
                            trade_type=TradeType.BUY,
                            amount=destination_amount,
                            rate=Price(origin_amount / destination_amount),
                            fee=Fee(fee),
                            fee_currency=fee_asset,
                            link='',
                            notes=notes,
                        )
                        self.db.add_trades([trade])
                    else:
                        log.debug(f'Ignoring trade with Destination Amount: {destination_amount}.')

    def import_uphold_transactions_csv(self, filepath: Path, **kwargs: Any) -> Tuple[bool, str]:
        """
        Information for the values that the columns can have has been obtained from sample CSVs
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_uphold_transaction(row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During uphold CSV import found action with unknown '
                        f'asset {e.asset_name}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during uphold CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except KeyError as e:
                    return False, str(e)
        return True, ''

    def _consume_bisq_trade(self, csv_row: Dict[str, Any], **kwargs: Any) -> None:
        """
        Consume the file containing only trades from Bisq.
        - UnknownAsset
        - DeserializationError
        """
        if csv_row['Status'] == 'Canceled':
            return
        formatstr = kwargs.get('timestamp_format')
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date/Time'],
            formatstr=formatstr if formatstr is not None else '%d %b %Y %H:%M:%S',
            location='Bisq',
        )
        # Get assets and amounts sold
        offer = csv_row['Offer type'].split()
        assets1_symbol, assets2_symbol = csv_row['Market'].split('/')
        if offer[0] == 'Sell':
            trade_type = TradeType.SELL
            if offer[1] == assets1_symbol:
                base_asset = symbol_to_asset_or_token(assets1_symbol)
                quote_asset = symbol_to_asset_or_token(assets2_symbol)
            else:
                base_asset = symbol_to_asset_or_token(assets2_symbol)
                quote_asset = symbol_to_asset_or_token(assets1_symbol)

            if base_asset == A_BTC:
                buy_amount = deserialize_asset_amount(csv_row['Amount'])
            else:
                buy_amount = deserialize_asset_amount(csv_row['Amount in BTC'])
        else:
            trade_type = TradeType.BUY
            if offer[1] == assets1_symbol:
                base_asset = symbol_to_asset_or_token(assets1_symbol)
                quote_asset = symbol_to_asset_or_token(assets2_symbol)
            else:
                base_asset = symbol_to_asset_or_token(assets2_symbol)
                quote_asset = symbol_to_asset_or_token(assets1_symbol)

            if base_asset == A_BTC:
                buy_amount = deserialize_asset_amount(csv_row['Amount in BTC'])
            else:
                buy_amount = deserialize_asset_amount(csv_row['Amount'])

        rate = Price(deserialize_asset_amount(csv_row['Price']))
        # Get trade fee
        if len(csv_row['Trade Fee BSQ']) != 0:
            fee_amount = deserialize_fee(csv_row['Trade Fee BSQ'])
            fee_currency = A_BSQ
        else:
            fee_amount = deserialize_fee(csv_row['Trade Fee BTC'])
            fee_currency = A_BTC

        trade = Trade(
            timestamp=timestamp,
            location=Location.BISQ,
            base_asset=base_asset,
            quote_asset=quote_asset,
            trade_type=trade_type,
            amount=buy_amount,
            rate=rate,
            fee=fee_amount,
            fee_currency=fee_currency,
            link='',
            notes=f'ID: {csv_row["Trade ID"]}',
        )
        self.db.add_trades([trade])

    def import_bisq_trades_csv(self, filepath: Path, **kwargs: Any) -> Tuple[bool, str]:
        """
        Import trades from bisq. The information and comments about this importer were addressed
        at the issue https://github.com/rotki/rotki/issues/824
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_bisq_trade(row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During Bisq CSV import found action with unknown '
                        f'asset {e.asset_name}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during Bisq CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except KeyError as e:
                    return False, str(e)
        return True, ''
