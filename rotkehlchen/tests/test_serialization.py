from rotkehlchen.fval import FVal
from rotkehlchen.utils.serialization import rkl_decode_value, rlk_jsondumps, rlk_jsonloads


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


def test_rlk_jsondumps():
    data = {
        'a': FVal('5.4'),
        'b': 'foo',
        'c': FVal('32.1'),
        'd': 5,
        'e': [1, 'a', FVal('5.1')],
    }
    result = rlk_jsondumps(data)
    assert result == '{"a": "5.4", "b": "foo", "c": "32.1", "d": 5, "e": [1, "a", "5.1"]}'
