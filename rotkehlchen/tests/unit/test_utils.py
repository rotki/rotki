import json
import time
from json.decoder import JSONDecodeError
from unittest.mock import patch

import pytest
from eth_typing import HexAddress, HexStr
from eth_utils import to_checksum_address
from hexbytes import HexBytes

from rotkehlchen.chain.ethereum.utils import generate_address_via_create2
from rotkehlchen.errors import ConversionError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_timestamp_from_date
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.utils.misc import (
    combine_dicts,
    combine_stat_dicts,
    convert_to_int,
    iso8601ts_to_timestamp,
    timestamp_to_date,
)
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn, cache_response_timewise
from rotkehlchen.utils.serialization import jsonloads_dict, jsonloads_list
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


def test_hexbytes_in_process_result():
    expected_str = '{"overview": "0xd4e56740f876aef8c010906a34"}'
    d = {'overview': HexBytes(b'\xd4\xe5g@\xf8v\xae\xf8\xc0\x10\x90j4')}
    assert json.dumps(process_result(d)) == expected_str


def test_iso8601ts_to_timestamp():
    assert iso8601ts_to_timestamp('2018-09-09T12:00:00.000Z') == 1536494400
    assert iso8601ts_to_timestamp('2011-01-01T04:13:22.220Z') == 1293855202
    assert iso8601ts_to_timestamp('1986-11-04T16:23:57.921Z') == 531505438
    # Timezone specific part of the test
    timezone_ts_str = '1997-07-16T22:30'
    timezone_ts_at_utc = 869092200
    assert iso8601ts_to_timestamp(timezone_ts_str + 'Z') == timezone_ts_at_utc
    # The utc offset for July should be time.altzone since it's in DST
    # https://stackoverflow.com/questions/3168096/getting-computers-utc-offset-in-python
    utc_offset = time.altzone
    assert iso8601ts_to_timestamp(timezone_ts_str) == timezone_ts_at_utc + utc_offset
    assert iso8601ts_to_timestamp('1997-07-16T22:30+01:00') == 869088600
    assert iso8601ts_to_timestamp('1997-07-16T22:30:45+01:00') == 869088645
    assert iso8601ts_to_timestamp('1997-07-16T22:30:45.1+01:00') == 869088645
    assert iso8601ts_to_timestamp('1997-07-16T22:30:45.01+01:00') == 869088645
    assert iso8601ts_to_timestamp('1997-07-16T22:30:45.001+01:00') == 869088645
    assert iso8601ts_to_timestamp('1997-07-16T22:30:45.9+01:00') == 869088646
    assert iso8601ts_to_timestamp('1997-07-16T22:30:45.99+01:00') == 869088646
    assert iso8601ts_to_timestamp('1997-07-16T22:30:45.999+01:00') == 869088646
    assert iso8601ts_to_timestamp('1997-07-16T21:30:45+00:00') == 869088645


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
    def mock_github_return_current(url):  # pylint: disable=unused-argument
        contents = '{"tag_name": "v1.4.0", "html_url": "https://foo"}'
        return MockResponse(200, contents)
    patch_github = patch('requests.get', side_effect=mock_github_return_current)

    def mock_system_spec():
        return {'rotkehlchen': 'v1.4.0'}
    patch_our_version = patch(
        'rotkehlchen.utils.version_check.get_system_spec',
        side_effect=mock_system_spec,
    )

    with patch_our_version, patch_github:
        result = check_if_version_up_to_date()
        assert result.download_url is None, 'Same version should return None as url'

    def mock_github_return(url):  # pylint: disable=unused-argument
        contents = '{"tag_name": "v99.99.99", "html_url": "https://foo"}'
        return MockResponse(200, contents)

    with patch('requests.get', side_effect=mock_github_return):
        result = check_if_version_up_to_date()
    assert result
    assert result[0]
    assert result.latest_version == 'v99.99.99'
    assert result.download_url == 'https://foo'

    # Also test that bad responses are handled gracefully
    def mock_non_200_github_return(url):  # pylint: disable=unused-argument
        contents = '{"tag_name": "v99.99.99", "html_url": "https://foo"}'
        return MockResponse(501, contents)

    with patch('requests.get', side_effect=mock_non_200_github_return):
        result = check_if_version_up_to_date()
        assert result.our_version
        assert not result.latest_version
        assert not result.latest_version

    def mock_missing_fields_github_return(url):  # pylint: disable=unused-argument
        contents = '{"html_url": "https://foo"}'
        return MockResponse(200, contents)

    with patch('requests.get', side_effect=mock_missing_fields_github_return):
        result = check_if_version_up_to_date()
        assert result.our_version
        assert not result.latest_version
        assert not result.latest_version

    def mock_invalid_json_github_return(url):  # pylint: disable=unused-argument
        contents = '{html_url: "https://foo"}'
        return MockResponse(200, contents)

    with patch('requests.get', side_effect=mock_invalid_json_github_return):
        result = check_if_version_up_to_date()
        assert result.our_version
        assert not result.latest_version
        assert not result.latest_version


class Foo(CacheableMixIn):
    def __init__(self):
        super().__init__()

        self.do_sum_call_count = 0
        self.do_something_call_count = 0
        self.do_something_arguments_dont_matter_count = 0

    @cache_response_timewise()
    def do_sum(self, arg1, arg2, **kwargs):  # pylint: disable=no-self-use, unused-argument
        self.do_sum_call_count += 1
        return arg1 + arg2

    @cache_response_timewise()
    def do_something(self, **kwargs):  # pylint: disable=unused-argument
        self.do_something_call_count += 1
        return 5

    @cache_response_timewise(arguments_matter=False)
    def do_something_arguments_dont_matter(self, arg1, arg2, **kwargs):  # pylint: disable=unused-argument  # noqa: E501
        self.do_something_arguments_dont_matter_count += 1
        return arg1 + arg2


def test_cache_response_timewise():
    """Test that cached value is called and not the function again"""
    instance = Foo()

    assert instance.do_something() == 5
    assert instance.do_something() == 5

    assert instance.do_something_call_count == 1


def test_cache_response_timewise_different_args():
    """Test that applying the cache timewise decorator works fine for different arguments

    Regression test for https://github.com/rotki/rotki/issues/543
    """
    instance = Foo()
    assert instance.do_sum(1, 1) == 2
    assert instance.do_sum(2, 2) == 4
    assert instance.do_sum_call_count == 2


def test_cache_response_timewise_ignore_cache():
    """Test that if the magic keyword argument `ignore_cache=True` is given the cache is ignored"""
    instance = Foo()

    assert instance.do_something() == 5
    assert instance.do_something(ignore_cache=True) == 5
    assert instance.do_something_call_count == 2

    assert instance.do_sum(1, 1) == 2
    assert instance.do_sum(1, 1) == 2
    assert instance.do_sum(1, 1, ignore_cache=True) == 2
    assert instance.do_sum_call_count == 2


def test_cache_response_timewise_with_arguments_matter_false():
    """Test that arguments_matter works as expected and if false we always get same result"""
    instance = Foo()

    assert instance.do_something_arguments_dont_matter(5, 6) == 11
    assert instance.do_something_arguments_dont_matter(1, 2) == 11
    assert instance.do_something_arguments_dont_matter(3, 4) == 11
    assert instance.do_something_arguments_dont_matter_count == 1

    assert instance.do_something_arguments_dont_matter(1, 2, ignore_cache=True) == 3
    assert instance.do_something_arguments_dont_matter_count == 2


def test_convert_to_int():
    assert convert_to_int('5') == 5
    assert convert_to_int('37451082560000003241000000000003221111111111') == 37451082560000003241000000000003221111111111  # noqa: E501
    with pytest.raises(ConversionError):
        assert convert_to_int(5.44, accept_only_exact=True) == 5
    assert convert_to_int(5.44, accept_only_exact=False) == 5
    assert convert_to_int(5.65, accept_only_exact=False) == 5
    with pytest.raises(ConversionError):
        assert convert_to_int(FVal('5.44'), accept_only_exact=True) == 5
    assert convert_to_int(FVal('5.44'), accept_only_exact=False) == 5
    assert convert_to_int(FVal('5.65'), accept_only_exact=False) == 5
    assert convert_to_int(FVal('4'), accept_only_exact=True) == 4
    assert convert_to_int(3) == 3
    with pytest.raises(ConversionError):
        assert convert_to_int('5.44', accept_only_exact=True) == 5
    assert convert_to_int('5.44', accept_only_exact=False) == 5
    assert convert_to_int('5.65', accept_only_exact=False) == 5
    assert convert_to_int('4', accept_only_exact=False) == 4
    with pytest.raises(ConversionError):
        assert convert_to_int(b'5.44', accept_only_exact=True) == 5
    assert convert_to_int(b'5.44', accept_only_exact=False) == 5
    assert convert_to_int(b'5.65', accept_only_exact=False) == 5
    assert convert_to_int(b'4', accept_only_exact=False) == 4


@pytest.mark.parametrize('address, salt, init_code, expected_contract_address', [
    (
        '0x0000000000000000000000000000000000000000',
        '0x0000000000000000000000000000000000000000000000000000000000000000',
        '0x00',
        '0x4D1A2e2bB4F88F0250f26Ffff098B0b30B26BF38',
    ),
    (
        '0xdeadbeef00000000000000000000000000000000',
        '0x0000000000000000000000000000000000000000000000000000000000000000',
        '0x00',
        '0xB928f69Bb1D91Cd65274e3c79d8986362984fDA3',
    ),
    (
        '0xdeadbeef00000000000000000000000000000000',
        '0x000000000000000000000000feed000000000000000000000000000000000000',
        '0x00',
        '0xD04116cDd17beBE565EB2422F2497E06cC1C9833',
    ),
    (
        '0x0000000000000000000000000000000000000000',
        '0x0000000000000000000000000000000000000000000000000000000000000000',
        '0xdeadbeef',
        '0x70f2b2914A2a4b783FaEFb75f459A580616Fcb5e',
    ),
    (
        '0x00000000000000000000000000000000deadbeef',
        '0x00000000000000000000000000000000000000000000000000000000cafebabe',
        '0xdeadbeef',
        '0x60f3f640a8508fC6a86d45DF051962668E1e8AC7',
    ),
    (
        '0x00000000000000000000000000000000deadbeef',
        '0x00000000000000000000000000000000000000000000000000000000cafebabe',
        '0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef',  # noqa: E501
        '0x1d8bfDC5D46DC4f61D6b6115972536eBE6A8854C',
    ),
    (
        '0x00000000000000000000000000000000DeaDBeef',
        '0x00000000000000000000000000000000000000000000000000000000cafebabe',
        '0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef',  # noqa: E501
        '0x1d8bfdc5d46dc4f61d6b6115972536ebe6a8854c',
    ),
    (
        '0x0000000000000000000000000000000000000000',
        '0x0000000000000000000000000000000000000000000000000000000000000000',
        '0x',
        '0xE33C0C7F7df4809055C3ebA6c09CFe4BaF1BD9e0',
    ),
])
def test_generate_address_via_create2(
        address,
        salt,
        init_code,
        expected_contract_address,
):
    """Test the CREATE2 opcode Python implementation.
    """
    contract_address = generate_address_via_create2(
        address=HexAddress(address),
        salt=HexStr(salt),
        init_code=HexStr(init_code),
    )
    assert contract_address == to_checksum_address(expected_contract_address)


def test_timestamp_to_date():
    date = timestamp_to_date(1611395717, formatstr='%d/%m/%Y %H:%M:%S %Z')
    assert not date.endswith(' '), 'Make sure %Z empty string is removed'


def test_deserialize_timestamp_from_date():
    timestamp = deserialize_timestamp_from_date(
        date='2020-10-06T20:46:48Z',  # failed in the past due to the trailing Z
        formatstr='%Y-%m-%dT%H:%M:%S',
        location='foo',
        skip_milliseconds=True,
    )
    assert timestamp == 1602017208


def test_jsonloads_dict():
    result = jsonloads_dict('{"foo": 1, "boo": "value"}')
    assert result == {'foo': 1, 'boo': 'value'}
    with pytest.raises(JSONDecodeError) as e:
        jsonloads_dict('["foo", "boo", 3]')
    assert 'Returned json is not a dict' in str(e.value)


def test_jsonloads_list():
    result = jsonloads_list('["foo", "boo", 3]')
    assert result == ["foo", "boo", 3]
    with pytest.raises(JSONDecodeError) as e:
        jsonloads_list('{"foo": 1, "boo": "value"}')
    assert 'Returned json is not a list' in str(e.value)
