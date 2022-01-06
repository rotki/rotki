import random
import warnings as test_warnings

import pytest
import requests

from rotkehlchen.chain.ethereum.modules.nfts import FREE_NFT_LIMIT
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)

TEST_ACC1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
TEST_ACC2 = '0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF'
TEST_ACC3 = '0xC21A5ee89D306353e065a6dd5779470DE395DBaC'


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('start_with_valid_premium', [bool(random.getrandbits(1))])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_query(rotkehlchen_api_server, start_with_valid_premium):
    async_query = bool(random.getrandbits(1))
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsresource',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=60)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    if len(result['addresses']) == 0:
        test_warnings.warn(UserWarning(f'Test account {TEST_ACC1} has no NFTs'))
        return

    if start_with_valid_premium is False:
        assert result['entries_found'] == result['entries_limit']
    else:
        assert result['entries_found'] > result['entries_limit']
    assert result['entries_limit'] == FREE_NFT_LIMIT
    assert result['entries_found'] == len(result['addresses'][TEST_ACC1])

    # find the one known nft in the nfts list
    nfts = result['addresses'][TEST_ACC1]
    nft_found = False
    for entry in nfts:
        if entry['token_identifier'] == '_nft_0xc3f733ca98e0dad0386979eb96fb1722a1a05e69_129':

            assert entry['name'] == 'MoonCat #129: 0x0082206dcb'
            assert entry['permalink'] == 'https://opensea.io/assets/0xc3f733ca98e0dad0386979eb96fb1722a1a05e69/129'  # noqa: E501
            assert entry['external_link'] == 'https://purrse.mooncat.community/129'
            assert entry['image_url'] == 'https://lh3.googleusercontent.com/C5ceArerHdGigmSt9tCsUD67Nbxr-P05fSsP_Pye34zN78lr2519P66kANkb55nfWW-ZMWFM4oCawLF4fW2jfRPxWButdqIX0QM95DM'  # noqa: E501
            assert FVal(entry['price_eth']) > ZERO
            assert FVal(entry['price_usd']) > ZERO
            assert entry['collection']['name'] == 'MoonCats'
            assert entry['collection']['banner_image'].startswith('https://')
            assert isinstance(entry['collection']['description'], str)
            assert entry['collection']['large_image'].startswith('https://')
            nft_found = True
            break

    assert nft_found, 'Could not find and verify the test NFT'


@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_query_after_account_add(rotkehlchen_api_server):
    """Test for https://github.com/rotki/rotki/issues/3590"""
    # add account 1
    data = {'accounts': [{'address': TEST_ACC1}]}
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=data)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsresource',
    ))
    result = assert_proper_response_with_result(response)

    if len(result['addresses']) == 0:
        test_warnings.warn(UserWarning(f'Test account {TEST_ACC1} has no NFTs'))
        return

    assert TEST_ACC1 in result['addresses']

    # now add another account and refresh NFTs, ignoring cache
    data = {'accounts': [{'address': TEST_ACC2}]}
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=data)
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'nftsresource',
        ), json={'ignore_cache': True},
    )
    result = assert_proper_response_with_result(response)
    assert TEST_ACC1 in result['addresses']
    assert TEST_ACC2 in result['addresses']


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC2, TEST_ACC3]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_ids_are_unique(rotkehlchen_api_server):
    """Check that if two accounts hold the same semi-fungible token we don't have duplicate ids"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsresource',
    ), json={'async_query': False})

    result = assert_proper_response_with_result(response)
    # get the ids from the query result
    ids_1 = [nft['token_identifier'] for nft in result['addresses'][TEST_ACC2]]
    ids_2 = [nft['token_identifier'] for nft in result['addresses'][TEST_ACC3]]
    # Check that two possible duplicates are between the NFT ids
    expected_id = '_nft_0xfaff15c6cdaca61a4f87d329689293e07c98f578_1'
    assert any([expected_id in nft_id for nft_id in ids_1])
    assert any([expected_id in nft_id for nft_id in ids_2])
    all_ids = ids_1 + ids_2
    set_of_ids = set(all_ids)
    assert len(all_ids) == len(set_of_ids)
