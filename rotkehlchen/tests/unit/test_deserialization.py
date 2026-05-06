import math

import pytest

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import (
    deserialize_timestamp,
    deserialize_timestamp_from_date_with_timezone,
)
from rotkehlchen.types import Timestamp, Timezone


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

    for bad_argument in (-1, FVal('3.14'), math.pi, '3.14', '5.23267356186572e+8', ['lol']):
        with pytest.raises(DeserializationError):
            deserialize_timestamp(bad_argument)


def test_deserialize_timestamp_from_date_with_timezone() -> None:
    """Test timezone-aware timestamp deserialization handles DST and explicit offsets."""
    assert deserialize_timestamp_from_date_with_timezone(
        date='2024-01-01 12:00:00',
        formatstr='%Y-%m-%d %H:%M:%S',
        location='test',
    ) == Timestamp(1704110400)
    assert deserialize_timestamp_from_date_with_timezone(
        date='2024-01-01 12:00:00',
        formatstr='%Y-%m-%d %H:%M:%S',
        location='test',
        timezone_name=Timezone('Europe/Madrid'),
    ) == Timestamp(1704106800)
    assert deserialize_timestamp_from_date_with_timezone(
        date='2024-07-01 12:00:00',
        formatstr='%Y-%m-%d %H:%M:%S',
        location='test',
        timezone_name=Timezone('Europe/Madrid'),
    ) == Timestamp(1719828000)
    assert deserialize_timestamp_from_date_with_timezone(
        date='2024-01-01 12:00:00 +0300',
        formatstr='%Y-%m-%d %H:%M:%S %z',
        location='test',
        timezone_name=Timezone('Europe/Madrid'),
    ) == Timestamp(1704099600)

    with pytest.raises(DeserializationError, match='Invalid timezone "Europe/Madird"'):
        deserialize_timestamp_from_date_with_timezone(
            date='2024-01-01 12:00:00',
            formatstr='%Y-%m-%d %H:%M:%S',
            location='test',
            timezone_name=Timezone('Europe/Madird'),
        )
