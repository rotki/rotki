import csv
from itertools import count
from pathlib import Path
from typing import Any, Dict, List

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, AssetMovementCategory, Trade
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
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
    elif entry == 'Kraken':
        return Location.KRAKEN
    elif entry == 'Poloniex':
        return Location.POLONIEX
    elif entry == 'Bittrex':
        return Location.BITTREX
    elif entry == 'Binance':
        return Location.BINANCE
    elif entry == 'Bitmex':
        return Location.BITMEX
    elif entry == 'Coinbase':
        return Location.COINBASE
    # TODO: Check if this is the correct string for CoinbasePro from cointracking
    elif entry == 'CoinbasePro':
        return Location.COINBASEPRO
    # TODO: Check if this is the correct string for Gemini from cointracking
    elif entry == 'Gemini':
        return Location.GEMINI
    elif entry == 'ETH Transaction':
        raise UnsupportedCointrackingEntry(
            'Not importing ETH Transactions from Cointracking. Cointracking does not '
            'export enough data for them. Simply enter your ethereum accounts and all '
            'your transactions will be auto imported directly from the chain',
        )
    elif entry == 'BTC Transaction':
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
        elif row_type == 'Deposit' or row_type == 'Withdrawal':
            category = deserialize_asset_movement_category(row_type.lower())
            if category == AssetMovementCategory.DEPOSIT:
                amount = deserialize_asset_amount(csv_row['Buy'])
                asset = Asset(csv_row['Cur.Buy'])
            else:
                amount = deserialize_asset_amount(csv_row['Sell'])
                asset = Asset(csv_row['Cur.Sell'])

            asset_movement = AssetMovement(
                location=location,
                category=category,
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

    def import_cointracking_csv(self, filepath: Path) -> None:
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

        return None

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

        # No fees info for now (Aug 2020) on crypto.com, so we put 0 fees
        fee = Fee(ZERO)
        fee_currency = A_USD  # whatever (used only if there is no fee)

        if row_type in (
            'crypto_purchase',
            'crypto_exchange',
            'referral_gift',
            'crypto_earn_interest_paid',
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

        elif row_type in (
            'crypto_earn_program_created',
            'lockup_lock',
            'lockup_unlock',
            'dynamic_coin_swap_bonus_exchange_deposit',
            'crypto_wallet_swap_debited',
            'crypto_wallet_swap_credited',
            'lockup_swap_debited',
            'lockup_swap_credited',
            'dynamic_coin_swap_debited',
            'dynamic_coin_swap_credited',
            'dynamic_coin_swap_bonus_exchange_deposit',
        ):
            # those types are ignored because it doesn't affect the wallet balance
            # or are not handled here
            return
        else:
            raise UnsupportedCryptocomEntry(
                f'Unknown entrype type "{row_type}" encountered during '
                f'cryptocom data import. Ignoring entry',
            )

    def _import_cryptocom_swap(self, data: Any) -> None:
        """Look for swapping events and handle them as trades.

        Notice: Crypto.com csv export gathers all swapping entries (`lockup_swap_*`,
        `crypto_wallet_swap_*`, ...) into one entry named `dynamic_coin_swap_*`.
        This method looks for `dynamic_coin_swap_debited` and `dynamic_coin_swap_credited`
        entries using the same timestamp to handle them as one trade.
        """
        swapping_rows: Dict[Any, Dict[str, Any]] = {}
        debited_row = None
        credited_row = None
        for row in data:
            if row['Transaction Kind'] == 'dynamic_coin_swap_debited':
                timestamp = deserialize_timestamp_from_date(
                    date=row['Timestamp (UTC)'],
                    formatstr='%Y-%m-%d %H:%M:%S',
                    location='crypto.com',
                )
                if timestamp not in swapping_rows:
                    swapping_rows[timestamp] = {}
                swapping_rows[timestamp]['debited'] = row
            elif row['Transaction Kind'] == 'dynamic_coin_swap_credited':
                timestamp = deserialize_timestamp_from_date(
                    date=row['Timestamp (UTC)'],
                    formatstr='%Y-%m-%d %H:%M:%S',
                    location='crypto.com',
                )
                if timestamp not in swapping_rows:
                    swapping_rows[timestamp] = {}
                swapping_rows[timestamp]['credited'] = row

        for timestamp in swapping_rows:
            credited_row = swapping_rows[timestamp]['credited']
            debited_row = swapping_rows[timestamp]['debited']
            if credited_row is not None and debited_row is not None:
                notes = 'Coin Swap\nSource: crypto.com (CSV import)'
                # No fees here since it's coin swapping
                fee = Fee(ZERO)
                fee_currency = A_USD

                base_asset = Asset(credited_row['Currency'])
                quote_asset = Asset(debited_row['Currency'])
                pair = TradePair(f'{base_asset.identifier}_{quote_asset.identifier}')
                base_amount_bought = deserialize_asset_amount(credited_row['Amount'])
                quote_amount_sold = deserialize_asset_amount(debited_row['Amount'])
                rate = Price(abs(base_amount_bought / quote_amount_sold))

                trade = Trade(
                    timestamp=timestamp,
                    location=Location.CRYPTOCOM,
                    pair=pair,
                    trade_type=TradeType.BUY,
                    amount=base_amount_bought,
                    rate=rate,
                    fee=fee,
                    fee_currency=fee_currency,
                    link='',
                    notes=notes,
                )
                self.db.add_trades([trade])

    def import_cryptocom_csv(self, filepath: Path) -> None:
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            self._import_cryptocom_swap(data)
            # reset the iterator
            csvfile.seek(0)
            # pass the header since seek(0) make the first row to be the header
            next(data)
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
        return None
