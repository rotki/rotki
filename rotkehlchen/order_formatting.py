from dataclasses import dataclass
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors import UnknownAsset, UnprocessableTradePair
from rotkehlchen.fval import FVal
from rotkehlchen.serializer import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
    deserialize_trade_type,
)
from rotkehlchen.typing import AssetAmount, Fee, Price, Timestamp, TradePair, TradeType
from rotkehlchen.user_messages import MessagesAggregator

ExchangeName = Literal['kraken', 'poloniex', 'bittrex', 'binance', 'bitmex']


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


class AssetMovement(NamedTuple):
    exchange: ExchangeName
    category: Literal['deposit', 'withdrawal']
    timestamp: Timestamp
    asset: Asset
    amount: FVal
    fee: Fee


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
    amount: AssetAmount
    rate: Price
    fee: Fee
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
    """We only support marging positions on poloniex and bitmex at the moment"""
    exchange: Literal['poloniex', 'bitmex']
    open_time: Optional[Timestamp]
    close_time: Timestamp
    profit_loss: FVal
    pl_currency: Asset
    notes: str


class Loan(NamedTuple):
    """We only support loans in poloniex at the moment"""
    open_time: Timestamp
    close_time: Timestamp
    currency: Asset
    fee: Fee
    earned: AssetAmount
    amount_lent: AssetAmount


def _split_pair(pair: TradePair) -> Tuple[str, str]:
    assets = pair.split('_')
    if len(assets) != 2:
        # Could not split the pair
        raise UnprocessableTradePair(pair)

    if len(assets[0]) == 0 or len(assets[1]) == 0:
        # no base or no quote asset
        raise UnprocessableTradePair(pair)

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


def deserialize_trade(data: Dict[str, Any]) -> Trade:
    """
    Takes a dict trade representation of our common trade format and serializes
    it into the Trade object

    May raise:
        - UnknownAsset: If the fee_currency string is not a known asset
        - DeserializationError: If any of the trade dict entries is not as expected
"""
    pair = data['pair']
    rate = deserialize_price(data['rate'])
    amount = deserialize_asset_amount(data['amount'])
    trade_type = deserialize_trade_type(data['trade_type'])

    trade_link = ''
    if 'link' in data:
        trade_link = data['link']
    trade_notes = ''
    if 'notes' in data:
        trade_notes = data['notes']

    return Trade(
        timestamp=data['timestamp'],
        location=data['location'],
        pair=pair,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=deserialize_fee(data['fee']),
        fee_currency=Asset(data['fee_currency']),
        link=trade_link,
        notes=trade_notes,
    )


def trades_from_dictlist(
        given_trades: List[Dict[str, Any]],
        start_ts: Timestamp,
        end_ts: Timestamp,
        location: str,
        msg_aggregator: MessagesAggregator,
) -> List[Trade]:
    """ Gets a list of dict trades, most probably read from the json files and
    a time period. Returns it as a list of the Trade tuples that are inside the time period

    Can raise:
      - KeyError: If a trade dict does not have a key as we expect it
    """
    returned_trades = list()
    for given_trade in given_trades:
        if given_trade['timestamp'] < start_ts:
            continue
        if given_trade['timestamp'] > end_ts:
            break

        try:
            returned_trades.append(deserialize_trade(given_trade))
        except UnknownAsset as e:
            msg_aggregator.add_warning(
                f'When processing {location} trades found a trade containing unknown '
                f'asset {e.asset_name}. Ignoring it.')
            continue

    return returned_trades


def asset_movements_from_dictlist(
        given_data: List[Dict[str, Any]],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> List[AssetMovement]:
    """ Gets a list of dict asset movements, most probably read from the json files and
    a time period. Returns it as a list of the AssetMovement tuples that are inside the time period

    May raise:
        - KeyError: If the given_data dict contains data in an unexpected format
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
            asset=Asset(movement['asset']),
            amount=FVal(movement['amount']),
            fee=Fee(FVal(movement['fee'])),
        ))
    return returned_movements
