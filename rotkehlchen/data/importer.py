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
            - UnknownAsset if one of the assets founds in the entry are not supported
        """
        row_type = csv_row['Type']
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr='%d.%m.%Y %H:%M',
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
            if not quote_asset and row_type not in ('Gift/Tip', 'Income'):
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
