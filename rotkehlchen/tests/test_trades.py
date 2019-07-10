import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import (
    Trade,
    deserialize_trade,
    trade_get_assets,
    trade_type_from_string,
    trades_from_dictlist,
)
from rotkehlchen.typing import Timestamp, TradePair, TradeType
from rotkehlchen.utils.serialization import rlk_jsondumps


def test_trade_type_from_string():
    assert trade_type_from_string('buy') == TradeType.BUY
    assert trade_type_from_string('sell') == TradeType.SELL
    assert trade_type_from_string('settlement_buy') == TradeType.SETTLEMENT_BUY
    assert trade_type_from_string('settlement_sell') == TradeType.SETTLEMENT_SELL

    assert len(list(TradeType)) == 4

    with pytest.raises(ValueError):
        trade_type_from_string('dsad')


def test_trade_type_to_string():
    assert str(TradeType.BUY) == 'buy'
    assert str(TradeType.SELL) == 'sell'
    assert str(TradeType.SETTLEMENT_BUY) == 'settlement_buy'
    assert str(TradeType.SETTLEMENT_SELL) == 'settlement_sell'


def test_trade_get_assets():
    trade = Trade(
        timestamp=1546985746,
        location='bittrex',
        pair=TradePair('BTC_ETH'),
        trade_type=TradeType.BUY,
        amount=FVal(10),
        rate=FVal(0.05),
        fee=FVal(0.001),
        fee_currency=A_ETH,
        link='',
        notes='',
    )
    a1, a2 = trade_get_assets(trade)
    assert isinstance(a1, Asset)
    assert a1 == A_BTC
    assert isinstance(a2, Asset)
    assert a2 == A_ETH


raw_trade1 = {
    'timestamp': 1516985746,
    'location': 'external',
    'pair': 'ETH_EUR',
    'trade_type': 'buy',
    'amount': '20.51',
    'rate': '134.1',
    'fee': '0.01',
    'fee_currency': 'ETH',
}

raw_trade2 = {
    'timestamp': 1537985746,
    'location': 'kraken',
    'pair': 'ETH_BTC',
    'trade_type': 'sell',
    'amount': '2.80',
    'rate': '0.1234',
    'fee': '0.01',
    'fee_currency': 'ETH',
    'link': 'a link can be here',
    'notes': 'notes can be here',
}

raw_trade3 = {
    'timestamp': 1557985746,
    'location': 'kraken',
    'pair': 'ETH_BTC',
    'trade_type': 'sell',
    'amount': '2.80',
    'rate': '0.1234',
    'fee': '0.01',
    'fee_currency': 'ETH',
    'link': 'a link can be here',
    'notes': 'notes can be here',
}


def test_deserialize_trade():
    trade1 = deserialize_trade(raw_trade1)
    assert isinstance(trade1, Trade)
    assert trade1.timestamp == Timestamp(1516985746)
    assert trade1.location == 'external'
    assert trade1.pair == TradePair('ETH_EUR')
    assert trade1.trade_type == TradeType.BUY
    assert trade1.amount == FVal('20.51')
    assert trade1.rate == FVal('134.1')
    assert trade1.fee == FVal('0.01')
    assert trade1.fee_currency == A_ETH
    assert trade1.link == ''
    assert trade1.notes == ''

    trade2 = deserialize_trade(raw_trade2)
    assert isinstance(trade2, Trade)
    assert trade2.timestamp == Timestamp(1537985746)
    assert trade2.location == 'kraken'
    assert trade2.pair == TradePair('ETH_BTC')
    assert trade2.trade_type == TradeType.SELL
    assert trade2.amount == FVal('2.80')
    assert trade2.rate == FVal('0.1234')
    assert trade2.fee == FVal('0.01')
    assert trade2.fee_currency == A_ETH
    assert trade2.link == 'a link can be here'
    assert trade2.notes == 'notes can be here'


def test_trades_from_dictlist():
    raw_trades = [raw_trade1, raw_trade2, raw_trade3]
    trades = trades_from_dictlist(raw_trades, 1516985747, 1557985736)
    assert len(trades) == 1
    assert isinstance(trades[0], Trade)


def test_serialize_deserialize_trade():
    trade = Trade(
        timestamp=Timestamp(1537985746),
        location='kraken',
        pair=TradePair('ETH_BTC'),
        trade_type=TradeType.SELL,
        amount=FVal('2.80'),
        rate=FVal('0.1234'),
        fee=FVal('0.01'),
        fee_currency=A_ETH,
        link='a link can be here',
        notes='notes can be here',
    )
    serialized_trade = rlk_jsondumps(trade._asdict())
    assert serialized_trade == rlk_jsondumps(raw_trade2)
    deserialized_trade = deserialize_trade(raw_trade2)
    assert deserialized_trade == trade
