import csv
import functools
import logging
from collections import defaultdict
from itertools import count
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, AssetMovementCategory, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.typing import AssetAmount, Fee, Location, Price, Timestamp, TradeType

log = logging.getLogger(__name__)


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
    # TODO: Check if this is the correct string for CoinbasePro from cointracking
    if entry == 'CoinbasePro':
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

    raise UnsupportedCSVEntry(
        f'Unknown Exchange "{entry}" encountered during a cointracking import. Ignoring it',
    )


class DataImporter():

    def __init__(self, db: DBHandler) -> None:
        self.db = db
        self.db_ledger = DBLedgerActions(self.db, self.db.msg_aggregator)

    def _consume_cointracking_entry(self, csv_row: Dict[str, Any]) -> None:
        """Consumes a cointracking entry row from the CSV and adds it into the database
        Can raise:
            - DeserializationError if something is wrong with the format of the expected values
            - UnsupportedCSVEntry if importing of this entry is not supported.
            - IndexError if the CSV file is corrupt
            - KeyError if the an expected CSV key is missing
            - UnknownAsset if one of the assets founds in the entry are not supported
        """
        row_type = csv_row['Type']
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr='%d.%m.%Y %H:%M:%S',
            location='cointracking.info',
        )
        notes = csv_row['Comment']
        location = exchange_row_to_location(csv_row['Exchange'])

        fee = Fee(ZERO)
        fee_currency = A_USD  # whatever (used only if there is no fee)
        if csv_row['Fee'] != '':
            fee = deserialize_fee(csv_row['Fee'])
            fee_currency = symbol_to_asset_or_token(csv_row['Cur.Fee'])

        if row_type in ('Gift/Tip', 'Trade', 'Income'):
            base_asset = symbol_to_asset_or_token(csv_row['Cur.Buy'])
            quote_asset = None if csv_row['Cur.Sell'] == '' else symbol_to_asset_or_token(csv_row['Cur.Sell'])  # noqa: E501
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
                asset = symbol_to_asset_or_token(csv_row['Cur.Buy'])
            else:
                amount = deserialize_asset_amount_force_positive(csv_row['Sell'])
                asset = symbol_to_asset_or_token(csv_row['Cur.Sell'])

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

    def import_cointracking_csv(self, filepath: Path) -> Tuple[bool, str]:
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.reader(csvfile, delimiter=',', quotechar='"')
            header = remap_header(next(data))
            for row in data:
                try:
                    self._consume_cointracking_entry(dict(zip(header, row)))
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

    def _consume_cryptocom_entry(self, csv_row: Dict[str, Any]) -> None:
        """Consumes a cryptocom entry row from the CSV and adds it into the database
        Can raise:
            - DeserializationError if something is wrong with the format of the expected values
            - UnsupportedCryptocomEntry if importing of this entry is not supported.
            - KeyError if the an expected CSV key is missing
            - UnknownAsset if one of the assets founds in the entry are not supported
            - sqlcipher.IntegrityError from db_ledger.add_ledger_action
        """
        row_type = csv_row['Transaction Kind']
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Timestamp (UTC)'],
            formatstr='%Y-%m-%d %H:%M:%S',
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
            'referral_gift',
            'referral_bonus',
            'crypto_earn_interest_paid',
            'referral_card_cashback',
            'card_cashback_reverted',
            'reimbursement',
        ):
            # variable mapping to raw data
            currency = csv_row['Currency']
            to_currency = csv_row['To Currency']
            native_currency = csv_row['Native Currency']
            amount = csv_row['Amount']
            to_amount = csv_row['To Amount']
            native_amount = csv_row['Native Amount']

            trade_type = TradeType.BUY if to_currency != native_currency else TradeType.SELL

            if row_type == 'crypto_exchange':
                # trades crypto to crypto
                base_asset = symbol_to_asset_or_token(to_currency)
                quote_asset = symbol_to_asset_or_token(currency)
                if quote_asset is None:
                    raise DeserializationError('Got a trade entry with an empty quote asset')
                base_amount_bought = deserialize_asset_amount(to_amount)
                quote_amount_sold = deserialize_asset_amount(amount)
            else:
                base_asset = symbol_to_asset_or_token(currency)
                quote_asset = symbol_to_asset_or_token(native_currency)
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

        elif row_type in ('crypto_withdrawal', 'crypto_deposit'):
            if row_type == 'crypto_withdrawal':
                category = AssetMovementCategory.WITHDRAWAL
                amount = deserialize_asset_amount_force_positive(csv_row['Amount'])
            else:
                category = AssetMovementCategory.DEPOSIT
                amount = deserialize_asset_amount(csv_row['Amount'])

            asset = symbol_to_asset_or_token(csv_row['Currency'])
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
        elif row_type in ('airdrop_to_exchange_transfer', 'mco_stake_reward'):
            asset = symbol_to_asset_or_token(csv_row['Currency'])
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
                notes=None,
            )
            self.db_ledger.add_ledger_action(action)
        elif row_type == 'invest_deposit':
            asset = symbol_to_asset_or_token(csv_row['Currency'])
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
            asset = symbol_to_asset_or_token(csv_row['Currency'])
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

    def _import_cryptocom_associated_entries(self, data: Any, tx_kind: str) -> None:
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
        for row in data:
            if row['Transaction Kind'] == f'{tx_kind}_debited':
                timestamp = deserialize_timestamp_from_date(
                    date=row['Timestamp (UTC)'],
                    formatstr='%Y-%m-%d %H:%M:%S',
                    location='cryptocom',
                )
                if timestamp not in multiple_rows:
                    multiple_rows[timestamp] = {}
                if 'debited' not in multiple_rows[timestamp]:
                    multiple_rows[timestamp]['debited'] = []
                multiple_rows[timestamp]['debited'].append(row)
            elif row['Transaction Kind'] == f'{tx_kind}_credited':
                # They only is one credited row
                timestamp = deserialize_timestamp_from_date(
                    date=row['Timestamp (UTC)'],
                    formatstr='%Y-%m-%d %H:%M:%S',
                    location='cryptocom',
                )
                if timestamp not in multiple_rows:
                    multiple_rows[timestamp] = {}
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
            debited_rows = multiple_rows[timestamp]['debited']
            credited_row = multiple_rows[timestamp]['credited']
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

                    base_asset = symbol_to_asset_or_token(credited_row['Currency'])
                    quote_asset = symbol_to_asset_or_token(debited_row['Currency'])
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
                    rate = Price(abs(base_amount_bought / quote_amount_sold))

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
                asset_object = symbol_to_asset_or_token(asset)
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
                        formatstr='%Y-%m-%d %H:%M:%S',
                        location='cryptocom',
                    ),
                )
                investments_rows = sorted(
                    investments_deposits[asset],
                    key=lambda x: deserialize_timestamp_from_date(
                        date=x['Timestamp (UTC)'],
                        formatstr='%Y-%m-%d %H:%M:%S',
                        location='cryptocom',
                    ),
                )
                last_date = Timestamp(0)
                for withdrawal in withdrawals_rows:
                    withdrawal_date = deserialize_timestamp_from_date(
                        date=withdrawal['Timestamp (UTC)'],
                        formatstr='%Y-%m-%d %H:%M:%S',
                        location='cryptocom',
                    )
                    amount_deposited = ZERO
                    for deposit in investments_rows:
                        deposit_date = deserialize_timestamp_from_date(
                            date=deposit['Timestamp (UTC)'],
                            formatstr='%Y-%m-%d %H:%M:%S',
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

    def import_cryptocom_csv(self, filepath: Path) -> Tuple[bool, str]:
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            try:
                #  Notice: Crypto.com csv export gathers all swapping entries (`lockup_swap_*`,
                # `crypto_wallet_swap_*`, ...) into one entry named `dynamic_coin_swap_*`.
                self._import_cryptocom_associated_entries(data, 'dynamic_coin_swap')
                # reset the iterator
                csvfile.seek(0)
                # pass the header since seek(0) make the first row to be the header
                next(data)

                self._import_cryptocom_associated_entries(data, 'dust_conversion')
                csvfile.seek(0)
                next(data)

                self._import_cryptocom_associated_entries(data, 'interest_swap')
                csvfile.seek(0)
                next(data)

                self._import_cryptocom_associated_entries(data, 'invest')
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
                    self._consume_cryptocom_entry(row)
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

    def _consume_blockfi_entry(self, csv_row: Dict[str, Any]) -> None:
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
            timestamp = deserialize_timestamp_from_date(
                date=csv_row['Confirmed At'],
                formatstr='%Y-%m-%d %H:%M:%S',
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

    def import_blockfi_transactions_csv(self, filepath: Path) -> Tuple[bool, str]:
        """
        Information for the values that the columns can have has been obtained from
        https://github.com/BittyTax/BittyTax/blob/06794f51223398759852d6853bc7112ffb96129a/bittytax/conv/parsers/blockfi.py#L67
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_blockfi_entry(row)
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

    def _consume_blockfi_trade(self, csv_row: Dict[str, Any]) -> None:
        """
        Consume the file containing only trades from BlockFi. As per my investigations
        (@yabirgb) this file can only contain confirmed trades.
        - UnknownAsset
        - DeserializationError
        """
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr='%Y-%m-%d %H:%M:%S',
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
            base_asset=buy_asset,
            quote_asset=sold_asset,
            trade_type=TradeType.BUY,
            amount=buy_amount,
            rate=rate,
            fee=None,  # BlockFI doesn't provide this information
            fee_currency=None,
            link='',
            notes=csv_row['Type'],
        )
        self.db.add_trades([trade])

    def import_blockfi_trades_csv(self, filepath: Path) -> Tuple[bool, str]:
        """
        Information for the values that the columns can have has been obtained from
        the issue in github #1674
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_blockfi_trade(row)
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

    def _consume_nexo(self, csv_row: Dict[str, Any]) -> None:
        """
        Consume CSV file from NEXO.
        This method can raise:
        - UnsupportedNexoEntry
        - UnknownAsset
        - DeserializationError
        - sqlcipher.IntegrityError from db_ledger.add_ledger_action
        """
        ignored_entries = ('ExchangeToWithdraw', 'DepositToExchange')

        if 'rejected' not in csv_row['Details']:
            timestamp = deserialize_timestamp_from_date(
                date=csv_row['Date / Time'],
                formatstr='%Y-%m-%d %H:%M:%S',
                location='NEXO',
            )
        else:
            log.debug(f'Ignoring rejected nexo entry {csv_row}')
            return

        asset = symbol_to_asset_or_token(csv_row['Currency'])
        amount = deserialize_asset_amount_force_positive(csv_row['Amount'])
        entry_type = csv_row['Type']
        transaction = csv_row['Transaction']

        if entry_type in ('Deposit', 'ExchangeDepositedOn', 'LockingTermDeposit'):
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
        elif entry_type in ('Interest', 'Bonus', 'Dividend'):
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

    def import_nexo_csv(self, filepath: Path) -> Tuple[bool, str]:
        """
        Information for the values that the columns can have has been obtained from
        https://github.com/BittyTax/BittyTax/blob/06794f51223398759852d6853bc7112ffb96129a/bittytax/conv/parsers/nexo.py
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_nexo(row)
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
