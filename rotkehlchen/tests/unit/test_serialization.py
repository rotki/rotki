import pytest

from rotkehlchen.balances.manual import ManuallyTrackedBalance, add_manually_tracked_balances
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import (
    deserialize_int_from_hex_or_int,
    deserialize_location,
    deserialize_trade_type,
)
from rotkehlchen.typing import Location, TradeType
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
    data = '{"a": "5.4", "b": "foo", "c": 32.1, "d": 5, "e": [1, "a", "5.1"], "f": "37451082560000003241"}'  # noqa: E501
    result = rlk_jsonloads(data)
    assert result == {
        'a': FVal('5.4'),
        'b': 'foo',
        'c': FVal('32.1'),
        'd': 5,
        'e': [1, 'a', FVal('5.1')],
        'f': 37451082560000003241,
    }


TEST_DATA = {
    'a': FVal('5.4'),
    'b': 'foo',
    'c': FVal('32.1'),
    'd': 5,
    'e': [1, 'a', FVal('5.1')],
    'f': A_ETH,
    A_BTC: 'test_with_asset_key',
}


def test_rlk_jsondumps():
    result = rlk_jsondumps(TEST_DATA)
    assert result == (
        '{"a": "5.4", "b": "foo", "c": "32.1", "d": 5, '
        '"e": [1, "a", "5.1"], "f": "ETH", "BTC": "test_with_asset_key"}'
    )


def test_pretty_json_dumps():
    """Simply test that pretty json dumps also works. That means that sorting
    of all serializable assets is enabled"""
    result = pretty_json_dumps(TEST_DATA)
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


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_deserialize_location(database):
    balances = []
    for idx, data in enumerate(Location):
        assert deserialize_location(str(data)) == data
        balances.append(ManuallyTrackedBalance(
            asset=A_BTC,
            label='Test' + str(idx),
            amount=FVal(1),
            location=data,
            tags=None,
        ))

    with pytest.raises(DeserializationError):
        deserialize_location('dsadsad')

    with pytest.raises(DeserializationError):
        deserialize_location(15)

    # Also write and read each location to DB to make sure that
    # location.serialize_for_db() and deserialize_location_from_db work fine
    add_manually_tracked_balances(database, balances)
    balances = database.get_manually_tracked_balances()
    for data in Location:
        assert data in (x.location for x in balances)


def test_deserialize_int_from_hex_or_int():
    # Etherscan can return logIndex 0x if it's the 0th log in the hash
    # https://etherscan.io/tx/0x6f1370cd9fa19d550031a30290b062dd3b56f44caf6344c05545ef15428de7ef
    assert deserialize_int_from_hex_or_int("0x", 'whatever') == 0
    assert deserialize_int_from_hex_or_int("0x1", 'whatever') == 1
    assert deserialize_int_from_hex_or_int("0x33", 'whatever') == 51
    assert deserialize_int_from_hex_or_int(66, 'whatever') == 66
