import pytest

from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serializer import deserialize_trade_type
from rotkehlchen.typing import TradeType
from rotkehlchen.utils.serialization import (
    pretty_json_dumps,
    rkl_decode_value,
    rlk_jsondumps,
    rlk_jsonloads,
)


def test_rkl_decode_value():
    assert rkl_decode_value(5.4) == FVal('5.4')
    assert rkl_decode_value('5.4') == FVal('5.4')
    assert rkl_decode_value(b'5.4') == FVal('5.4')
    assert rkl_decode_value(b'foo') == b'foo'
    assert rkl_decode_value('foo') == 'foo'
    assert rkl_decode_value(5) == 5


def test_rlk_jsonloads():
    data = '{"a": "5.4", "b": "foo", "c": 32.1, "d": 5, "e": [1, "a", "5.1"]}'
    result = rlk_jsonloads(data)
    assert result == {
        'a': FVal('5.4'),
        'b': 'foo',
        'c': FVal('32.1'),
        'd': 5,
        'e': [1, 'a', FVal('5.1')],
    }


data = {
    'a': FVal('5.4'),
    'b': 'foo',
    'c': FVal('32.1'),
    'd': 5,
    'e': [1, 'a', FVal('5.1')],
    'f': A_ETH,
    A_BTC: 'test_with_asset_key',
}


def test_rlk_jsondumps():
    result = rlk_jsondumps(data)
    assert result == (
        '{"a": "5.4", "b": "foo", "c": "32.1", "d": 5, '
        '"e": [1, "a", "5.1"], "f": "ETH", "BTC": "test_with_asset_key"}'
    )


def test_pretty_json_dumps():
    """Simply test that pretty json dumps also works. That means that sorting
    of all serializable assets is enabled"""
    result = pretty_json_dumps(data)
    assert result


def test_deserialize_trade_type():
    assert deserialize_trade_type('buy') == TradeType.BUY
    assert deserialize_trade_type('sell') == TradeType.SELL
    assert deserialize_trade_type('settlement_buy') == TradeType.SETTLEMENT_BUY
    assert deserialize_trade_type('settlement_sell') == TradeType.SETTLEMENT_SELL

    assert len(list(TradeType)) == 4

    with pytest.raises(DeserializationError):
        deserialize_trade_type('dsad')

    with pytest.raises(DeserializationError):
        deserialize_trade_type(None)

    with pytest.raises(DeserializationError):
        deserialize_trade_type(1)
