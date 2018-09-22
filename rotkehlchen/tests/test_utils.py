import json

import pytest

from rotkehlchen.fval import FVal
from rotkehlchen.server import process_result
from rotkehlchen.utils import iso8601ts_to_timestamp


def test_process_result():
    d = {
        'overview': {
            'foo': FVal(1.0),
        },
        'all_events': {
            'boo': FVal(1.0),
            'something': [
                {'a': 'a', 'f': FVal(1.0)},
                {'b': 'b', 'f': FVal(2.0)},
            ]
        },
    }

    # Without process result should throw an error but with it no
    with pytest.raises(TypeError):
        json.dumps(d)

    json.dumps(process_result(d))


def test_tuple_in_process_result():
    d = {'overview': [{'foo': (FVal('0.1'),)}]}

    # Process result should detect the tuple and throw
    with pytest.raises(ValueError):
        json.dumps(process_result(d))


def test_iso8601ts_to_timestamp():
    assert iso8601ts_to_timestamp('2018-09-09T12:00:00.000Z') == 1536494400
    assert iso8601ts_to_timestamp('2011-01-01T04:13:22.220Z') == 1293855202
    assert iso8601ts_to_timestamp('1986-11-04T16:23:57.921Z') == 531505437
