from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.db.filtering import TradesFilterQuery
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.exchanges.data_structures import Trade, deserialize_trade, trades_from_dictlist
from rotkehlchen.fval import FVal
from rotkehlchen.types import ExchangeLocationID, Location, Timestamp, TradeType
from rotkehlchen.utils.serialization import rlk_jsondumps


def test_trade_type_to_string():
    assert str(TradeType.BUY) == 'buy'
    assert str(TradeType.SELL) == 'sell'
    assert str(TradeType.SETTLEMENT_BUY) == 'settlement buy'
    assert str(TradeType.SETTLEMENT_SELL) == 'settlement sell'


raw_trade1 = {
    'timestamp': 1516985746,
    'location': 'external',
    'base_asset': 'ETH',
    'quote_asset': 'EUR',
    'trade_type': 'buy',
    'amount': '20.51',
    'rate': '134.1',
    'fee': '0.01',
    'fee_currency': 'ETH',
}

raw_trade2 = {
    'timestamp': 1537985746,
    'location': 'kraken',
    'base_asset': 'ETH',
    'quote_asset': 'BTC',
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
    'base_asset': 'ETH',
    'quote_asset': 'BTC',
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
    assert trade1.location == Location.EXTERNAL
    assert trade1.base_asset == A_ETH
    assert trade1.quote_asset == A_EUR
    assert trade1.trade_type == TradeType.BUY
    assert trade1.amount == FVal('20.51')
    assert trade1.rate == FVal('134.1')
    assert trade1.fee == FVal('0.01')
    assert trade1.fee_currency == A_ETH
    assert isinstance(trade1.fee_currency, Asset)
    assert trade1.link == ''
    assert trade1.notes == ''

    trade2 = deserialize_trade(raw_trade2)
    assert isinstance(trade2, Trade)
    assert trade2.timestamp == Timestamp(1537985746)
    assert trade2.location == Location.KRAKEN
    assert trade2.base_asset == A_ETH
    assert trade2.quote_asset == A_BTC
    assert trade2.trade_type == TradeType.SELL
    assert trade2.amount == FVal('2.80')
    assert trade2.rate == FVal('0.1234')
    assert trade2.fee == FVal('0.01')
    assert trade2.fee_currency == A_ETH
    assert isinstance(trade2.fee_currency, Asset)
    assert trade2.link == 'a link can be here'
    assert trade2.notes == 'notes can be here'

    another_raw_trade = raw_trade2.copy()
    another_raw_trade['fee_currency'] = 'UNKNOWN'
    with pytest.raises(UnknownAsset):
        deserialize_trade(another_raw_trade)


def test_trades_from_dictlist(function_scope_messages_aggregator):
    raw_trades = [raw_trade1, raw_trade2, raw_trade3]
    trades = trades_from_dictlist(
        given_trades=raw_trades,
        start_ts=1516985747,
        end_ts=1557985736,
        location='test',
        msg_aggregator=function_scope_messages_aggregator,
    )
    assert len(trades) == 1
    assert isinstance(trades[0], Trade)


def test_serialize_deserialize_trade():
    trade = Trade(
        timestamp=Timestamp(1537985746),
        location=Location.KRAKEN,
        base_asset=A_ETH,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('2.80'),
        rate=FVal('0.1234'),
        fee=FVal('0.01'),
        fee_currency=A_ETH,
        link='a link can be here',
        notes='notes can be here',
    )
    serialized_trade = rlk_jsondumps(trade.serialize())
    assert serialized_trade == rlk_jsondumps(raw_trade2)
    deserialized_trade = deserialize_trade(raw_trade2)
    assert deserialized_trade == trade


@pytest.mark.parametrize('db_settings', [
    {'non_syncing_exchanges': [ExchangeLocationID(name='FTX', location=Location.FTX)]}])
def test_query_trade_history_online_but_exchange_excluded(events_historian):
    """Test that if an online refresh of trades for an exchange is requested,
    that exchange is not connected, but is also at the excluded exchanges we
    don't end up querying trades of all exchanges"""

    patch_latest_trades = patch.object(events_historian, 'query_location_latest_trades')
    patch_iterate_exchanges = patch.object(events_historian.exchange_manager, 'iterate_exchanges')

    with patch_latest_trades as latest_trades_mock, patch_iterate_exchanges as iterate_exchanges_mock:  # noqa: E501
        events_historian.query_trades(
            filter_query=TradesFilterQuery.make(location=Location.FTX),
            only_cache=False,
        )

    assert latest_trades_mock.call_count == 0
    assert iterate_exchanges_mock.call_count == 0
