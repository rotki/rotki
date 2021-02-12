import csv
import functools
from itertools import count
from pathlib import Path
from typing import Any, Dict, List, Tuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
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
from rotkehlchen.typing import AssetAmount, Fee, Location, Price, TradePair, TradeType


def remap_header(fieldnames: List[str]) -> List[str]:
    cur_count = count(1)
    mapping = {1: 'Buy', 2: 'Sell', 3: 'Fee'}
    return [f'Cur.{mapping[next(cur_count)]}' if f.startswith('Cur.') else f for f in fieldnames]


class UnsupportedCointrackingEntry(Exception):
    """Thrown for Cointracking CSV export entries we can't support to import"""


class UnsupportedCryptocomEntry(Exception):
    """Thrown for Cryptocom CSV export entries we can't support to import"""


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
        raise UnsupportedCointrackingEntry(
            'Not importing ETH Transactions from Cointracking. Cointracking does not '
            'export enough data for them. Simply enter your ethereum accounts and all '
            'your transactions will be auto imported directly from the chain',
        )
    if entry == 'BTC Transaction':
        raise UnsupportedCointrackingEntry(
            'Not importing BTC Transactions from Cointracking. Cointracking does not '
            'export enough data for them. Simply enter your BTC accounts and all '
            'your transactions will be auto imported directly from the chain',
        )

    raise UnsupportedCointrackingEntry(
        f'Unknown Exchange "{entry}" encountered during a cointracking import. Ignoring it',
    )


class DataImporter():

    def __init__(self, db: DBHandler) -> None:
        self.db = db

    def _consume_cointracking_entry(self, csv_row: Dict[str, Any]) -> None:
        """Consumes a cointracking entry row from the CSV and adds it into the database
        Can raise:
            - DeserializationError if something is wrong with the format of the expected values
            - UnsupportedCointrackingEntry if importing of this entry is not supported.
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
            fee_currency = Asset(csv_row['Cur.Fee'])

        if row_type in ('Gift/Tip', 'Trade', 'Income'):
            base_asset = Asset(csv_row['Cur.Buy'])
            quote_asset = None if csv_row['Cur.Sell'] == '' else Asset(csv_row['Cur.Sell'])
            if quote_asset is None and row_type not in ('Gift/Tip', 'Income'):
                raise DeserializationError('Got a trade entry with an empty quote asset')

            if quote_asset is None:
                # Really makes no difference as this is just a gift and the amount is zero
                quote_asset = A_USD
            pair = TradePair(f'{base_asset.identifier}_{quote_asset.identifier}')
            base_amount_bought = deserialize_asset_amount(csv_row['Buy'])
            if csv_row['Sell'] != '-':
                quote_amount_sold = deserialize_asset_amount(csv_row['Sell'])
            else:
                quote_amount_sold = AssetAmount(ZERO)
            rate = Price(quote_amount_sold / base_amount_bought)

            trade = Trade(
                timestamp=timestamp,
                location=location,
                pair=pair,
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
                asset = Asset(csv_row['Cur.Buy'])
            else:
                amount = deserialize_asset_amount_force_positive(csv_row['Sell'])
                asset = Asset(csv_row['Cur.Sell'])

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
            raise UnsupportedCointrackingEntry(
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
                except UnsupportedCointrackingEntry as e:
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
        """
        row_type = csv_row['Transaction Kind']
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Timestamp (UTC)'],
            formatstr='%Y-%m-%d %H:%M:%S',
            location='crypto.com',
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
                base_asset = Asset(to_currency)
                quote_asset = Asset(currency)
                if quote_asset is None:
                    raise DeserializationError('Got a trade entry with an empty quote asset')
                base_amount_bought = deserialize_asset_amount(to_amount)
                quote_amount_sold = deserialize_asset_amount(amount)
            else:
                base_asset = Asset(currency)
                quote_asset = Asset(native_currency)
                base_amount_bought = deserialize_asset_amount(amount)
                quote_amount_sold = deserialize_asset_amount(native_amount)

            rate = Price(abs(quote_amount_sold / base_amount_bought))
            pair = TradePair(f'{base_asset.identifier}_{quote_asset.identifier}')
            trade = Trade(
                timestamp=timestamp,
                location=Location.CRYPTOCOM,
                pair=pair,
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

            asset = Asset(csv_row['Currency'])
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
        ):
            # those types are ignored because it doesn't affect the wallet balance
            # or are not handled here
            return
        else:
            raise UnsupportedCryptocomEntry(
                f'Unknown entrype type "{row_type}" encountered during '
                f'cryptocom data import. Ignoring entry',
            )

    def _import_cryptocom_associated_entries(self, data: Any, tx_kind: str) -> None:
        """Look for events that have associated entries and handle them as trades.

        This method looks for `*_debited` and `*_credited` entries using the
        same timestamp to handle them as one trade.

        Known kind: 'dynamic_coin_swap' or 'dust_conversion'
        """
        multiple_rows: Dict[Any, Dict[str, Any]] = {}
        debited_row = None
        credited_row = None
        for row in data:
            if row['Transaction Kind'] == f'{tx_kind}_debited':
                timestamp = deserialize_timestamp_from_date(
                    date=row['Timestamp (UTC)'],
                    formatstr='%Y-%m-%d %H:%M:%S',
                    location='crypto.com',
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
                    location='crypto.com',
                )
                if timestamp not in multiple_rows:
                    multiple_rows[timestamp] = {}
                multiple_rows[timestamp]['credited'] = row

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
                FVal('0'),
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

                    base_asset = Asset(credited_row['Currency'])
                    quote_asset = Asset(debited_row['Currency'])
                    pair = TradePair(f'{base_asset.identifier}_{quote_asset.identifier}')
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
                        pair=pair,
                        trade_type=TradeType.BUY,
                        amount=AssetAmount(base_amount_bought),
                        rate=rate,
                        fee=fee,
                        fee_currency=fee_currency,
                        link='',
                        notes=notes,
                    )
                    self.db.add_trades([trade])

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
            except KeyError as e:
                return False, str(e)

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
                except UnsupportedCryptocomEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                    continue
                except KeyError as e:
                    return False, str(e)
        return True, ''
