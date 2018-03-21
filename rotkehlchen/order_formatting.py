from collections import namedtuple
from rotkehlchen.fval import FVal

Events = namedtuple('Events', ('buys', 'sells'))
BuyEvent = namedtuple(
    'BuyEvent', (
        'timestamp',
        'amount',  # Amout of the asset being bought
        'rate',  # Rate in 'profit_currency' for which we buy 1 unit of the buying asset
        'fee_rate',  # Fee rate in 'profit_currency' which we paid for each unit of the buying asset
        'cost')  # Total cost in profit currency for this trade
)
SellEvent = namedtuple('SellEvent', (
    'timestamp',
    'amount',  # Amount of the asset we sell
    'rate',  # Rate in 'profit_currency' for which we sell 1 unit of the sold asset
    'fee_rate',  # Fee rate in 'profit_currency' which we paid for each unit of the sold asset
    'gain')  # Total gain in profit currency for this trade
)
Trade = namedtuple(
    'Trade',
    (
        'timestamp',
        'pair',
        'type',
        'rate',  # always in quote currency?
        'cost', # TODO: Make sure is this total cost with fees or without fees, for all exchanges?
        'cost_currency',
        'fee',
        'fee_currency',
        'amount',
        'location'
    )
)

AssetMovement = namedtuple(
    'AssetMovement',
    (
        'exchange',
        'category',
        'timestamp',
        'asset',
        'amount',
        'fee',
    )
)


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

        returned_trades.append(Trade(
            timestamp=given_trade['timestamp'],
            pair=given_trade['pair'],
            type=given_trade['type'],
            rate=FVal(given_trade['rate']),
            cost=FVal(given_trade['cost']),
            cost_currency=given_trade['cost_currency'],
            fee=FVal(given_trade['fee']),
            fee_currency=given_trade['fee_currency'],
            amount=FVal(given_trade['amount']),
            location=given_trade['location']
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
