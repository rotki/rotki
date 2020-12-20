from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.ethereum.tokens import EthTokens
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.blockchain import mock_etherscan_query
from rotkehlchen.tests.utils.factories import make_ethereum_address


@pytest.fixture(name='ethtokens')
def fixture_ethtokens(ethereum_manager, database):
    return EthTokens(database, ethereum_manager)


def test_detect_tokens_for_addresses(ethtokens, inquirer):  # pylint: disable=unused-argument
    """
    Autodetect tokens of two addresses

    This is going to be a bit slow test since it actually queries etherscan without any mocks.
    By doing so we can test that the whole behavior with etherscan works fine and our
    chosen chunk length for it is also acceptable.

    USD price queries are mocked so we don't care about the result.
    Just check that all prices are included


    """
    addr1 = '0x0000000000000000000000000000000000000000'
    addr2 = '0xD3A962916a19146D658de0ab62ee237ed3115873'
    result, token_usd_prices = ethtokens.query_tokens_for_addresses([addr1, addr2], False)

    assert len(result[addr1]) >= 170
    balance = result[addr1]['BAT']
    assert isinstance(balance, FVal)
    assert balance > FVal('478763')  # BAT burned at time of test writing
    assert len(result[addr2]) >= 20

    assert len(token_usd_prices) == len(set(result[addr1].keys()).union(set(result[addr2].keys())))


def test_detected_tokens_cache(ethtokens, inquirer):  # pylint: disable=unused-argument
    """Test that a cache of the detected tokens is created and used at subsequent queries.

    Also test that the cache can be ignored and recreated with a forced redetection
    """
    addr1 = make_ethereum_address()
    addr2 = make_ethereum_address()
    eth_map = {addr1: {'GNO': 5000, 'MKR': 4000}, addr2: {'MKR': 6000}}
    etherscan_patch = mock_etherscan_query(
        eth_map=eth_map,
        etherscan=ethtokens.ethereum.etherscan,
        original_queries=None,
        original_requests_get=requests.get,
    )
    ethtokens_max_chunks_patch = patch(
        'rotkehlchen.chain.ethereum.tokens.ETHERSCAN_MAX_TOKEN_CHUNK_LENGTH',
        new=800,
    )

    with ethtokens_max_chunks_patch, etherscan_patch as etherscan_mock:
        # Initially autodetect the tokens at the first call
        result1, _ = ethtokens.query_tokens_for_addresses([addr1, addr2], False)
        initial_call_count = etherscan_mock.call_count

        # Then in second call autodetect queries should not have been made, and DB cache used
        result2, _ = ethtokens.query_tokens_for_addresses([addr1, addr2], False)
        call_count = etherscan_mock.call_count
        assert call_count == initial_call_count + 2

        # In the third call force re-detection
        result3, _ = ethtokens.query_tokens_for_addresses([addr1, addr2], True)
        call_count = etherscan_mock.call_count
        assert call_count == initial_call_count + 2 + initial_call_count

        assert result1 == result2 == result3
        assert len(result1) == len(eth_map)
        for key, entry in result1.items():
            eth_map_entry = eth_map[key]
            assert len(entry) == len(eth_map_entry)
            for token, val in entry.items():
                assert token_normalized_value(eth_map_entry[token], token) == val
