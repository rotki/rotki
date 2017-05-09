from collections import namedtuple

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
        'cost',
        'cost_currency',
        'fee',
        'fee_currency',
        'amount',
        'location'
    )
)


def trade_get_other_pair(trade, asset):
    currencies = trade.pair.split('_')
    if len(currencies) != 2:
        raise ValueError("Could not split {} pair".format(trade.pair))
    return currencies[0] if currencies[1] == asset else currencies[1]


def trade_get_assets(trade):
    currencies = trade.pair.split('_')
    if len(currencies) != 2:
        raise ValueError("Could not split {} pair".format(trade.pair))

    return currencies[0], currencies[1]
