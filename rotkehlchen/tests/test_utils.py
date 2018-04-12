import pytest
import json

from rotkehlchen.server import process_result
from rotkehlchen.fval import FVal


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
