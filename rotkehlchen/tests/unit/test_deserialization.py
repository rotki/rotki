import pytest

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import Timestamp


def test_deserialize_timestamp():
    """Test various edge cases of deserialize timestamp and that they all work as expected"""
    target_ts = Timestamp(1492980000)
    ts_from_scientific_str = deserialize_timestamp('1.49298E+9')
    assert ts_from_scientific_str == target_ts
    ts_from_normal_str = deserialize_timestamp('1492980000')
    assert ts_from_normal_str == target_ts
    ts_from_normal_int = deserialize_timestamp(1492980000)
    assert ts_from_normal_int == target_ts
    ts_from_normal_scientific = deserialize_timestamp(1.49298E+9)
    assert ts_from_normal_scientific == target_ts

    for bad_argument in (-1, FVal('3.14'), 3.14, '3.14', '5.23267356186572e+8', ['lol']):
        with pytest.raises(DeserializationError):
            deserialize_timestamp(bad_argument)
