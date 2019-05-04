from collections import namedtuple
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from dataclasses import dataclass

from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Timestamp, TradePair, TradeType


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BuyEvent:
    timestamp: Timestamp
    amount: FVal  # Amount of the asset being bought
    rate: FVal  # Rate in quote currency for which we buy 1 unit of the buying asset
    # Fee rate in profit currency which we paid for each unit of the buying asset
    fee_rate: FVal


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class SellEvent:
    timestamp: Timestamp
    amount: FVal  # Amount of the asset we sell
    rate: FVal  # Rate in 'profit_currency' for which we sell 1 unit of the sold asset
    fee_rate: FVal  # Fee rate in 'profit_currency' which we paid for each unit of the sold asset
    gain: FVal  # Gain in profit currency for this trade. Fees are not counted here.


class Events(NamedTuple):
    buys: List[BuyEvent]
    sells: List[SellEvent]


AssetMovement = namedtuple(
    'AssetMovement',
    (
        'exchange',
        'category',
        'timestamp',
        'asset',
        'amount',
        'fee',
    ),
)


def trade_type_from_string(symbol: str) -> TradeType:
    """Take a string and attempts to turn it into a TradeType"""
    if symbol == 'buy':
        return TradeType.BUY
    elif symbol == 'sell':
        return TradeType.SELL
    elif symbol == 'settlement_buy':
        return TradeType.SETTLEMENT_BUY
    elif symbol == 'settlement_sell':
        return TradeType.SETTLEMENT_SELL
    else:
        raise ValueError(f'Unknown symbol {symbol} for trade type')


class Trade(NamedTuple):
    """Represents a Trade

    Pairs are represented as BASE_QUOTE. When a buy is made, then the BASE
    asset is bought with QUOTE asset. When a sell is made then the BASE
    asset is sold for QUOTE asset.

    Exchanges don't use the same part of the pair to denote the same thing. For
    example in Poloniex the pair is called BTC_ETH and you buy and sell ETH for
    BTC. In Kraken XXBTZEUR translates to BTC_EUR. This means we buy BTC for EUR
    or we sell BTC for EUR. So for some exchanges like poloniex when importing a
    trade, the pair needs to be swapped.
    """
    timestamp: Timestamp
    location: str
    pair: TradePair
    trade_type: TradeType
    # The amount represents the amount bought if it's a buy or or the amount
    # sold if it's a sell
    amount: FVal
    rate: FVal
    fee: FVal
    fee_currency: Asset
    link: str = ''
    notes: str = ''

    @property
    def base_asset(self) -> Asset:
        base, _ = pair_get_assets(self.pair)
        return base

    @property
    def quote_asset(self) -> Asset:
        _, quote = pair_get_assets(self.pair)
        return quote


class MarginPosition(NamedTuple):
    exchange: str
    open_time: Optional[Timestamp]
    close_time: Timestamp
    profit_loss: FVal
    pl_currency: Asset
    notes: str


def _split_pair(pair: TradePair) -> Tuple[str, str]:
    assets = pair.split('_')
    if len(assets) != 2:
        raise ValueError(f'Could not split {pair} pair')

    if len(assets[0]) == 0:
        raise ValueError(f'Splitting {pair} yielded no base asset')

    if len(assets[1]) == 0:
        raise ValueError(f'Splitting {pair} yielded no quote asset')

    return assets[0], assets[1]


def trade_pair_from_assets(base: Asset, quote: Asset) -> TradePair:
    return TradePair(f'{base.identifier}_{quote.identifier}')


def pair_get_assets(pair: TradePair) -> Tuple[Asset, Asset]:
    """Returns a tuple with the (base, quote) assets"""
    base_str, quote_str = _split_pair(pair)

    base_asset = Asset(base_str)
    quote_asset = Asset(quote_str)
    return base_asset, quote_asset


def invert_pair(pair: TradePair) -> TradePair:
    left, right = pair_get_assets(pair)
    return trade_pair_from_assets(right, left)


def get_pair_position_str(pair: TradePair, position: str) -> str:
    """Get the string representation of an asset of a trade pair"""
    assert position == 'first' or position == 'second'
    base_str, quote_str = _split_pair(pair)
    return base_str if position == 'first' else quote_str


def get_pair_position_asset(pair: TradePair, position: str) -> Asset:
    """
    Get the asset of a trade pair.

    Can throw UnknownAsset if the asset is not known to Rotkehlchen
    """
    return Asset(get_pair_position_str(pair, position))


def trade_get_assets(trade: Trade) -> Tuple[Asset, Asset]:
    return pair_get_assets(trade.pair)


def trades_from_dictlist(
        given_trades: List[Dict[str, Any]],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> List[Trade]:
    """ Gets a list of dict trades, most probably read from the json files and
    a time period. Returns it as a list of the Trade tuples that are inside the time period
    """
    returned_trades = list()
    for given_trade in given_trades:
        if given_trade['timestamp'] < start_ts:
            continue
        if given_trade['timestamp'] > end_ts:
            break

        pair = given_trade['pair']
        rate = FVal(given_trade['rate'])
        amount = FVal(given_trade['amount'])
        trade_type = trade_type_from_string(given_trade['type'])

        trade_link = ''
        if 'link' in given_trade:
            trade_link = given_trade['link']
        trade_notes = ''
        if 'notes' in given_trade:
            trade_notes = given_trade['notes']

        returned_trades.append(Trade(
            timestamp=given_trade['timestamp'],
            location=given_trade['location'],
            pair=pair,
            trade_type=trade_type,
            amount=amount,
            rate=rate,
            fee=FVal(given_trade['fee']),
            fee_currency=given_trade['fee_currency'],
            link=trade_link,
            notes=trade_notes,
        ))
    return returned_trades


def asset_movements_from_dictlist(
        given_data: List[Dict[str, Any]],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> List[AssetMovement]:
    """ Gets a list of dict asset movements, most probably read from the json files and
    a time period. Returns it as a list of the AssetMovement tuples that are inside the time period
    """
    returned_movements = list()
    for movement in given_data:
        if movement['timestamp'] < start_ts:
            continue
        if movement['timestamp'] > end_ts:
            break

        returned_movements.append(AssetMovement(
            exchange=movement['exchange'],
            category=movement['category'],
            timestamp=movement['timestamp'],
            asset=movement['asset'],
            amount=FVal(movement['amount']),
            fee=FVal(movement['fee']),
        ))
    return returned_movements
