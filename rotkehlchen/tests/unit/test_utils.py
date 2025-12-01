import json
import operator
import sys
from collections import defaultdict
from datetime import datetime
from json.decoder import JSONDecodeError
from unittest.mock import patch

import pytest
from eth_typing import HexAddress, HexStr
from eth_utils import to_checksum_address
from hexbytes import HexBytes
from packaging.version import Version

from rotkehlchen.chain.ethereum.utils import generate_address_via_create2
from rotkehlchen.constants.assets import A_USDC
from rotkehlchen.constants.resolver import identifier_to_evm_address
from rotkehlchen.errors.serialization import ConversionError
from rotkehlchen.externalapis.github import Github
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_timestamp_from_date
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.utils.misc import (
    combine_dicts,
    combine_nested_dicts_inplace,
    convert_to_int,
    is_production,
    iso8601ts_to_timestamp,
    pairwise,
    pairwise_longest,
    timestamp_to_date,
)
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn, cache_response_timewise
from rotkehlchen.utils.serialization import jsonloads_dict, jsonloads_list
from rotkehlchen.utils.version_check import get_current_version


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
    utc_offset = datetime.fromtimestamp(timezone_ts_at_utc).astimezone().utcoffset().total_seconds()  # noqa: E501
    assert iso8601ts_to_timestamp(timezone_ts_str) == timezone_ts_at_utc - utc_offset
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


def test_check_if_version_up_to_date():
    def mock_github_return_current(url, **kwargs):  # pylint: disable=unused-argument
        contents = '{"tag_name": "v1.4.0", "html_url": "https://foo"}'
        return MockResponse(200, contents)
    patch_github = patch('requests.get', side_effect=mock_github_return_current)

    def mock_system_spec():
        return {'rotkehlchen': 'v1.4.0'}
    patch_our_version = patch(
        'rotkehlchen.utils.version_check.get_system_spec',
        side_effect=mock_system_spec,
    )
    result = get_current_version()  # check calling without Github arg works
    assert result.our_version is not None

    github = Github()
    with patch_our_version, patch_github:
        result = get_current_version(github=github)
        assert result.download_url is None, 'Same version should return None as url'

    def mock_github_return(url, **kwargs):  # pylint: disable=unused-argument
        contents = '{"tag_name": "v99.99.99", "html_url": "https://foo"}'
        return MockResponse(200, contents)

    with patch('requests.get', side_effect=mock_github_return):
        result = get_current_version(github=github)
    assert result
    assert result[0]
    assert result.latest_version == Version('v99.99.99')  # check v prefix does not matter
    assert result.latest_version == Version('99.99.99')
    assert result.download_url == 'https://foo'

    # Also test that bad responses are handled gracefully
    def mock_non_200_github_return(url, **kwargs):  # pylint: disable=unused-argument
        contents = '{"tag_name": "v99.99.99", "html_url": "https://foo"}'
        return MockResponse(501, contents)

    with patch('requests.get', side_effect=mock_non_200_github_return):
        result = get_current_version(github=github)
        assert result.our_version
        assert not result.latest_version
        assert not result.latest_version

    def mock_missing_fields_github_return(url, **kwargs):  # pylint: disable=unused-argument
        contents = '{"html_url": "https://foo"}'
        return MockResponse(200, contents)

    with patch('requests.get', side_effect=mock_missing_fields_github_return):
        result = get_current_version(github=github)
        assert result.our_version
        assert not result.latest_version
        assert not result.latest_version

    def mock_invalid_json_github_return(url, **kwargs):  # pylint: disable=unused-argument
        contents = '{html_url: "https://foo"}'
        return MockResponse(200, contents)

    with patch('requests.get', side_effect=mock_invalid_json_github_return):
        result = get_current_version(github=github)
        assert result.our_version
        assert not result.latest_version
        assert not result.latest_version


def test_is_production():
    """Test the dev version check in is_production"""
    version_str = 'v1.32.0'

    def mock_system_spec():
        nonlocal version_str
        return {'rotkehlchen': version_str}

    patch_our_version = patch(
        'rotkehlchen.utils.version_check.get_system_spec',
        side_effect=mock_system_spec,
    )
    sys.frozen = True
    with patch_our_version:
        assert is_production() is True

    version_str = '1.32.1.dev8+g3c097f01e.d20240217'
    with patch_our_version:
        assert is_production() is False  # version is non production

    delattr(sys, 'frozen')
    version_str = 'v1.32.0'
    with patch_our_version:
        assert is_production() is False  # even if full tag, when not frozen not production


class Foo(CacheableMixIn):
    def __init__(self):
        super().__init__()

        self.do_sum_call_count = 0
        self.do_something_call_count = 0
        self.do_something_arguments_dont_matter_count = 0

    @cache_response_timewise()
    def do_sum(self, arg1, arg2, **kwargs):  # pylint: disable=unused-argument
        self.do_sum_call_count += 1
        return arg1 + arg2

    @cache_response_timewise()
    def do_something(self, **kwargs):  # pylint: disable=unused-argument
        self.do_something_call_count += 1
        return 5

    @cache_response_timewise(arguments_matter=False)
    def do_something_arguments_dont_matter(self, arg1, arg2, **kwargs):  # pylint: disable=unused-argument
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


@pytest.mark.parametrize(('address', 'salt', 'init_code', 'is_init_code_hashed', 'expected_contract_address'), [  # noqa: E501
    (
        '0x0000000000000000000000000000000000000000',
        '0x0000000000000000000000000000000000000000000000000000000000000000',
        '0x00',
        False,
        '0x4D1A2e2bB4F88F0250f26Ffff098B0b30B26BF38',
    ),
    (
        '0xdeadbeef00000000000000000000000000000000',
        '0x0000000000000000000000000000000000000000000000000000000000000000',
        '0x00',
        False,
        '0xB928f69Bb1D91Cd65274e3c79d8986362984fDA3',
    ),
    (
        '0xdeadbeef00000000000000000000000000000000',
        '0x000000000000000000000000feed000000000000000000000000000000000000',
        '0x00',
        False,
        '0xD04116cDd17beBE565EB2422F2497E06cC1C9833',
    ),
    (
        '0x0000000000000000000000000000000000000000',
        '0x0000000000000000000000000000000000000000000000000000000000000000',
        '0xdeadbeef',
        False,
        '0x70f2b2914A2a4b783FaEFb75f459A580616Fcb5e',
    ),
    (
        '0x00000000000000000000000000000000deadbeef',
        '0x00000000000000000000000000000000000000000000000000000000cafebabe',
        '0xdeadbeef',
        False,
        '0x60f3f640a8508fC6a86d45DF051962668E1e8AC7',
    ),
    (
        '0x00000000000000000000000000000000deadbeef',
        '0x00000000000000000000000000000000000000000000000000000000cafebabe',
        '0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
        False,
        '0x1d8bfDC5D46DC4f61D6b6115972536eBE6A8854C',
    ),
    (
        '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',  # Uniswap V2 Factory
        '0xd257ccbe93e550a27236e8cc4971336f6cd2d53037ad567f10fbcc28df6a1eb1',
        '0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f',  # Uniswap V2 Factory Init Code  # noqa: E501
        True,
        '0xAE461cA67B15dc8dc81CE7615e0320dA1A9aB8D5',  # DAI-USDC V2 pool
    ),

    (
        '0x1F98431c8aD98523631AE4a59f267346ea31F984',  # Uniswap V3 Factory
        '0xb4dd6f5d729bba20de462c8f8999dc56e24bcda0735b09dd34f3939eaec37999',
        '0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54',  # Uniswap V3 Factory Init Code  # noqa: E501
        True,
        '0xCBCdF9626bC03E24f779434178A73a0B4bad62eD',
    ),
])
def test_generate_address_via_create2(
        address,
        salt,
        init_code,
        is_init_code_hashed,
        expected_contract_address,
):
    """Test the CREATE2 opcode Python implementation."""
    contract_address = generate_address_via_create2(
        address=HexAddress(address),
        salt=HexStr(salt),
        init_code=HexStr(init_code),
        is_init_code_hashed=is_init_code_hashed,
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
    assert result == ['foo', 'boo', 3]
    with pytest.raises(JSONDecodeError) as e:
        jsonloads_list('{"foo": 1, "boo": "value"}')
    assert 'Returned json is not a list' in str(e.value)


@pytest.mark.vcr
def test_retrieve_old_erc20_token_info(ethereum_inquirer):
    info = ethereum_inquirer.get_erc20_contract_info('0x2C4Bd064b998838076fa341A83d007FC2FA50957')
    assert info['symbol'] == 'UNI-V1'
    assert info['name'] == 'Uniswap V1'


def test_pairwise():
    a = [1, 2, 3, 4, 5, 6]
    assert [x + y for x, y in pairwise(a)] == [3, 7, 11]
    assert [x + y for x, y in pairwise_longest(a)] == [3, 7, 11]

    a = [1, 2, 3, 4, 5]
    assert [x + y for x, y in pairwise(a)] == [3, 7]
    assert list(pairwise_longest(a)) == [(1, 2), (3, 4), (5, None)]


def test_combine_nested_dicts_inplace():
    # basic addition
    result_1 = combine_nested_dicts_inplace(
        a=defaultdict(lambda: defaultdict(int), {
            'A': defaultdict(int, {'X': 10, 'Y': 20}),
            'B': defaultdict(int, {'X': 100}),
        }),
        b=defaultdict(lambda: defaultdict(int), {
            'A': defaultdict(int, {'X': 5, 'Z': 50}),
            'C': defaultdict(int, {'Z': 200}),
        }),
        op=operator.add,
    )
    assert result_1 == {
        'A': {'X': 15, 'Y': 20, 'Z': 50},
        'B': {'X': 100},
        'C': {'Z': 200},
    }

    # basic subtraction
    result_2 = combine_nested_dicts_inplace(
        a=defaultdict(lambda: defaultdict(int), {
            'A': defaultdict(int, {'X': 10, 'Y': 20}),
            'B': defaultdict(int, {'X': 100}),
        }),
        b=defaultdict(lambda: defaultdict(int), {
            'A': defaultdict(int, {'X': 5, 'Z': 50}),
            'C': defaultdict(int, {'Z': 200}),
        }),
        op=operator.sub,
    )
    assert result_2 == {
        'A': {'X': 5, 'Y': 20, 'Z': -50},
        'B': {'X': 100},
        'C': {'Z': -200},
    }

    # edge case - `b` is empty
    result_3 = combine_nested_dicts_inplace(
        a=defaultdict(lambda: defaultdict(int), {'A': defaultdict(int, {'X': 10})}),
        b=defaultdict(lambda: defaultdict(int)),
        op=operator.add,
    )
    assert result_3 == {'A': {'X': 10}}

    # edge case - `a` is empty
    result_4 = combine_nested_dicts_inplace(
        a=defaultdict(lambda: defaultdict(float)),
        b=defaultdict(lambda: defaultdict(float), {
            'A': defaultdict(float, {'X': 5.5, 'Z': 50.1}),
            'C': defaultdict(float, {'Z': 200.2}),
        }),
        op=operator.add,
    )
    assert result_4 == {'A': {'X': 5.5, 'Z': 50.1}, 'C': {'Z': 200.2}}

    # edge case - `a` is empty, with subtraction
    result_5 = combine_nested_dicts_inplace(
        a=defaultdict(lambda: defaultdict(int)),
        b=defaultdict(lambda: defaultdict(int), {'A': defaultdict(int, {'X': 5, 'Z': 50})}),
        op=operator.sub,
    )
    assert result_5 == {'A': {'X': -5, 'Z': -50}}

    # edge case - default factory is used for new inner keys
    # `b` has an inner dict for 'A', but 'A' in `a` is missing the 'Z' key
    result_6 = combine_nested_dicts_inplace(
        a=defaultdict(lambda: defaultdict(int), {'A': defaultdict(int, {'X': 10})}),
        b=defaultdict(lambda: defaultdict(int), {'A': defaultdict(int, {'Z': 50})}),
        op=operator.add,
    )
    assert result_6 == {'A': {'X': 10, 'Z': 50}}


def test_identifier_to_evm_address():
    """Test various identifier_to_evm_address conversions.
    Checks that valid erc20 and erc721 identifiers get the correct address and also
    that a number of invalid identifiers return None without raising exceptions.
    """
    assert identifier_to_evm_address(
        identifier=A_USDC.identifier,
    ) == A_USDC.resolve_to_evm_token().evm_address
    assert identifier_to_evm_address(
        identifier=f'eip155:1/erc721:{(erc721_address := make_evm_address())}/1234',
    ) == erc721_address

    # check various invalid identifiers to ensure they return None without raising exceptions.
    assert identifier_to_evm_address(identifier='') is None
    assert identifier_to_evm_address(identifier='xyz:1/erc20:0x1B073382E63411E3BcfFE90aC1B9A43feFa1Ec6F') is None  # noqa: E501
    assert identifier_to_evm_address(identifier='1/erc20:0x1B073382E63411E3BcfFE90aC1B9A43feFa1Ec6F') is None  # noqa: E501
    assert identifier_to_evm_address(identifier='eip155:1:erc20:0x1B073382E63411E3BcfFE90aC1B9A43feFa1Ec6F') is None  # noqa: E501
    assert identifier_to_evm_address(identifier='eip155:/:') is None
    assert identifier_to_evm_address(identifier='eip155:1/erc20:') is None
    assert identifier_to_evm_address(identifier='eip155:1/erc20:xyz') is None
