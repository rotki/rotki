import json
from unittest.mock import patch

import pytest

from rotkehlchen.errors import UnprocessableTradePair
from rotkehlchen.exchanges.data_structures import invert_pair
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.utils.misc import (
    combine_dicts,
    combine_stat_dicts,
    get_system_spec,
    iso8601ts_to_timestamp,
)
from rotkehlchen.utils.version_check import check_if_version_up_to_date


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
            ],
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


def test_invert_pair():
    assert invert_pair('BTC_ETH') == 'ETH_BTC'
    assert invert_pair('XMR_EUR') == 'EUR_XMR'
    with pytest.raises(UnprocessableTradePair):
        assert invert_pair('sdsadasd')


def test_combine_dicts():
    a = {'a': 1, 'b': 2, 'c': 3}
    b = {'a': 4, 'c': 2}
    result = combine_dicts(a, b)
    assert result == {'a': 5, 'b': 2, 'c': 5}


def test_combine_stat_dicts():
    a = {
        'EUR': {'amount': FVal('50.5'), 'usd_value': FVal('200.1')},
        'BTC': {'amount': FVal('2.5'), 'usd_value': FVal('12200.5')},
    }
    b = {
        'RDN': {'amount': FVal('15.5'), 'usd_value': FVal('105.9')},
    }
    c = {
        'EUR': {'amount': FVal('15.5'), 'usd_value': FVal('105.9')},
        'BTC': {'amount': FVal('3.5'), 'usd_value': FVal('18200.5')},
        'ETH': {'amount': FVal('100.1'), 'usd_value': FVal('11200.1')},
    }
    result = combine_stat_dicts([a, b, c])
    assert result == {
        'EUR': {'amount': FVal('66'), 'usd_value': FVal('306')},
        'RDN': {'amount': FVal('15.5'), 'usd_value': FVal('105.9')},
        'ETH': {'amount': FVal('100.1'), 'usd_value': FVal('11200.1')},
        'BTC': {'amount': FVal('6'), 'usd_value': FVal('30401')},
    }


def test_check_if_version_up_to_date():
    assert check_if_version_up_to_date() is None, 'Current version should always be up to date'

    def mock_github_return(url):
        contents = '{"tag_name": "v99.99.99", "html_url": "https://foo"}'
        return MockResponse(200, contents)

    with patch('requests.get', side_effect=mock_github_return):
        msg = check_if_version_up_to_date()
    assert 'is outdated' in msg
    assert 'The latest version is v99.99.99 and you can download it from https://foo' in msg

    # Also test that bad responses are handled gracefully
    def mock_non_200_github_return(url):
        contents = '{"tag_name": "v99.99.99", "html_url": "https://foo"}'
        return MockResponse(501, contents)

    with patch('requests.get', side_effect=mock_non_200_github_return):
        msg = check_if_version_up_to_date()
        assert not msg

    def mock_missing_fields_github_return(url):
        contents = '{"html_url": "https://foo"}'
        return MockResponse(200, contents)

    with patch('requests.get', side_effect=mock_missing_fields_github_return):
        msg = check_if_version_up_to_date()
        assert not msg

    def mock_invalid_json_github_return(url):
        contents = '{html_url: "https://foo"}'
        return MockResponse(200, contents)

    with patch('requests.get', side_effect=mock_invalid_json_github_return):
        msg = check_if_version_up_to_date()
        assert not msg
