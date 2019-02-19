from collections import namedtuple
from typing import List, NamedTuple, Optional

from dataclasses import dataclass

from rotkehlchen import typing
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Trade


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BuyEvent:
    timestamp: typing.Timestamp
    amount: FVal  # Amount of the asset being bought
    rate: FVal  # Rate in quote currency for which we buy 1 unit of the buying asset
    # Fee rate in profit currency which we paid for each unit of the buying asset
    fee_rate: FVal


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class SellEvent:
    timestamp: typing.Timestamp
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


class MarginPosition(NamedTuple):
    exchange: str
    open_time: Optional[typing.Timestamp]
    close_time: typing.Timestamp
    profit_loss: FVal
    pl_currency: typing.Asset
    notes: str


def trade_get_other_pair(trade, asset):
    currencies = trade.pair.split('_')
    if len(currencies) != 2:
        raise ValueError("Could not split {} pair".format(trade.pair))
    return currencies[0] if currencies[1] == asset else currencies[1]


def pair_get_assets(pair):
    currencies = pair.split('_')
    if len(currencies) != 2:
        raise ValueError("Could not split {} pair".format(pair))

    return currencies[0], currencies[1]


def trade_get_assets(trade):
    return pair_get_assets(trade.pair)


def trades_from_dictlist(given_trades, start_ts, end_ts):
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
            trade_type=given_trade['type'],
            amount=amount,
            rate=rate,
            fee=FVal(given_trade['fee']),
            fee_currency=given_trade['fee_currency'],
            link=trade_link,
            notes=trade_notes,
        ))
    return returned_trades


def asset_movements_from_dictlist(given_data, start_ts, end_ts):
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
