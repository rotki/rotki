import random
import warnings as test_warnings

import pytest
import requests

from rotkehlchen.chain.ethereum.nft import FREE_NFT_LIMIT
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)

TEST_ACC1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('start_with_valid_premium', [bool(random.getrandbits(1))])
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
    for entry in nfts:
        if entry['token_identifier'] == '8636':
            assert entry['name'] == 'BASTARD GAN PUNK V2 #8636'
            assert entry['permalink'] == 'https://opensea.io/assets/0x31385d3520bced94f77aae104b406994d8f2168c/8636'  # noqa: E501
            assert entry['external_link'] == 'https://www.bastardganpunks.club/v2/8636'
            assert entry['image_url'] == 'https://lh3.googleusercontent.com/kwF-39qZlluEalQnNv-yMxbntzNdc3g00pK2xALkpoir9ooWttVUO2hVFWOgPtOkJOHufYRajfn-nNFdjruRQ4YaMgOYHEB8E4CdjBk'  # noqa: E501
            assert FVal(entry['price_eth']) > ZERO
            assert FVal(entry['price_usd']) > ZERO
            break
