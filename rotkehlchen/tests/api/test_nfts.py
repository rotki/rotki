import random
import warnings as test_warnings
from unittest.mock import patch

import pytest
import requests
from flaky import flaky

from rotkehlchen.chain.ethereum.modules.nfts import FREE_NFT_LIMIT
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.externalapis.opensea import NFT, Collection
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
TEST_ACC4 = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # yabir.eth
NFT_ID_FOR_TEST_ACC4 = '_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041'  # noqa: E501


@flaky(max_runs=3, min_passes=1)  # all opensea calls have become quite flaky
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

    if start_with_valid_premium is False:
        return  # test nft may not fit in results without premium

    # else find the one known nft in the nfts list
    nfts = result['addresses'][TEST_ACC1]
    nft_found = False
    for entry in nfts:
        if entry['token_identifier'] == '_nft_0xc3f733ca98e0dad0386979eb96fb1722a1a05e69_129':

            assert entry['name'] == 'MoonCat #129: 0x0082206dcb'
            assert entry['external_link'] == 'https://purrse.mooncat.community/129'
            assert 'image_url' in entry
            assert FVal(entry['price_eth']) > ZERO
            assert FVal(entry['price_usd']) > ZERO
            assert entry['collection']['name'] == 'MoonCats'
            assert entry['collection']['banner_image'].startswith('https://')
            assert isinstance(entry['collection']['description'], str)
            assert entry['collection']['large_image'].startswith('https://')
            nft_found = True
            break

    assert nft_found, 'Could not find and verify the test NFT'


@flaky(max_runs=3, min_passes=1)  # all opensea calls have become quite flaky
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


@flaky(max_runs=3, min_passes=1)  # all opensea calls have become quite flaky
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


@flaky(max_runs=3, min_passes=1)  # all opensea calls have become quite flaky
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_balances_and_prices(rotkehlchen_api_server):
    """Check that nfts balances return the expected fields. Also check nft prices"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False})

    result = assert_proper_response_with_result(response)
    for nfts_balances in result.values():
        for nft_balance in nfts_balances:
            if nft_balance['id'] == NFT_ID_FOR_TEST_ACC4:
                assert nft_balance['name'] == 'yabir.eth'
                assert nft_balance['collection_name'] == 'ENS: Ethereum Name Service'
                assert nft_balance['is_lp'] is False

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftspricesresource',
    ))
    result = assert_proper_response_with_result(response)[0]
    expected_result = {
        'asset': '_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041',  # noqa: E501
        'manually_input': False,
        'price_asset': 'ETH',
    }
    price = result.pop('price_in_asset')
    price_usd = result.pop('usd_price')
    assert expected_result == result
    assert FVal(price) > 0
    assert FVal(price_usd) > 0


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
@pytest.mark.parametrize('endpoint', ['nftsbalanceresource', 'nftsresource'])
def test_nfts_ignoring_works(rotkehlchen_api_server, endpoint):
    """Check that ignoring NFTs work as expected"""
    def mock_get_all_nft_data(addresses, **kwargs):  # pylint: disable=unused-argument
        nft_map = {
            '0xc37b40ABdB939635068d3c5f13E7faF686F03B65': [
                NFT(
                    token_identifier='_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041',  # noqa: E501
                    background_color=None,
                    image_url='https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg',  # noqa: E501
                    name='yabir.eth',
                    external_link='https://app.ens.domains/name/yabir.eth',
                    permalink='https://opensea.io/assets/ethereum/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/26612040215479394739615825115912800930061094786769410446114278812336794170041',  # noqa: E501
                    price_eth=FVal(0.0006899),
                    price_usd=FVal(1.056568052),
                    collection=Collection(
                        name='ENS: Ethereum Name Service',
                        banner_image='',
                        description='Ethereum Name Service (ENS) domains are secure domain names for the decentralized world. ENS domains provide a way for users to map human readable names to blockchain and non-blockchain resources, like Ethereum addresses, IPFS hashes, or website URLs. ENS domains can be bought and sold on secondary markets.',  # noqa: E501
                        large_image='https://i.seadn.io/gae/BBj09xD7R4bBtg1lgnAAS9_TfoYXKwMtudlk-0fVljlURaK7BWcARCpkM-1LGNGTAcsGO6V1TgrtmQFvCo8uVYW_QEfASK-9j6Nr?w=500&auto=format',  # noqa: E501
                        floor_price=FVal(0.0006899),
                    ),
                ),
            ],
        }
        return nft_map, 1

    get_all_nft_data_patch = patch('rotkehlchen.chain.ethereum.modules.nfts.Nfts._get_all_nft_data', side_effect=mock_get_all_nft_data)  # noqa: E501

    # ignore the nft
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredassetsresource',
        ),
        json={'assets': [NFT_ID_FOR_TEST_ACC4]},
    )
    result = assert_proper_response_with_result(response)
    assert NFT_ID_FOR_TEST_ACC4 in result

    # query the nfts endpoint and verify that the nft is not present
    with get_all_nft_data_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                endpoint,
            ),
            json={'async_query': False},
        )
        result = assert_proper_response_with_result(response)
        if endpoint == 'nftsresource':
            all_nfts_ids = {nft['token_identifier'] for nft in result['addresses'][TEST_ACC4]}
            assert NFT_ID_FOR_TEST_ACC4 not in all_nfts_ids
        else:
            assert result == {}

    # remove the nft from the ignored list.
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredassetsresource',
        ),
        json={'assets': [NFT_ID_FOR_TEST_ACC4]},
    )
    result = assert_proper_response_with_result(response)
    assert NFT_ID_FOR_TEST_ACC4 not in result

    # query the nfts endpoint again and verify that the nft is present
    with get_all_nft_data_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                endpoint,
            ),
            json={'async_query': False},
        )
        result = assert_proper_response_with_result(response)
        if endpoint == 'nftsresource':
            all_nfts_ids = {nft['token_identifier'] for nft in result['addresses'][TEST_ACC4]}
        else:
            all_nfts_ids = {nft['id'] for nft in result[TEST_ACC4]}
        assert NFT_ID_FOR_TEST_ACC4 in all_nfts_ids
