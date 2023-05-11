import random
import warnings as test_warnings
from typing import Any
from unittest.mock import patch

import pytest
import requests
from flaky import flaky

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import LiquidityPoolAsset
from rotkehlchen.chain.ethereum.modules.nft.constants import FREE_NFT_LIMIT
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.chain.ethereum.modules.uniswap.v3.types import NFTLiquidityPool
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.externalapis.opensea import NFT, Collection
from rotkehlchen.fval import FVal
from rotkehlchen.tests.conftest import TestEnvironment, requires_env
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Price

TEST_ACC1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'  # lefteris.eth
TEST_ACC2 = '0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF'
TEST_ACC3 = '0xC21A5ee89D306353e065a6dd5779470DE395DBaC'
TEST_ACC4 = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # yabir.eth
TEST_ACC5 = '0x4bBa290826C253BD854121346c370a9886d1bC26'  # nebolax.eth
TEST_ACC6 = '0x3e649c5Eac6BBEE8a4F2A2945b50d8e582faB3bf'  # contains a uniswap-v3 nft
NFT_ID_FOR_TEST_ACC4 = '_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041'  # noqa: E501
NFT_ID_FOR_TEST_ACC5 = '_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_73552724610198397480670284492690114609730214421511097849210414928326607694469'  # noqa: E501
NFT_ID_FOR_TEST_ACC6_1 = '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_360680'
NFT_ID_FOR_TEST_ACC6_2 = '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_360762'

TEST_NFT_NEBOLAX_ETH = NFT(
    token_identifier='_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_73552724610198397480670284492690114609730214421511097849210414928326607694469',  # noqa: E501
    background_color=None,
    image_url='https://openseauserdata.com/files/8fd18b22e4c81aff3998956e7a712d93.svg',
    name='nebolax.eth',
    external_link='https://app.ens.domains/name/nebolax.eth',
    permalink='https://opensea.io/assets/ethereum/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/73552724610198397480670284492690114609730214421511097849210414928326607694469',  # noqa: E501
    price_eth=FVal(0.0012),
    price_usd=FVal(1.2379458),
    collection=Collection(
        name='ENS: Ethereum Name Service',
        banner_image=None,
        description='Ethereum Name Service (ENS) domains are secure domain names for the decentralized world. ENS domains provide a way for users to map human readable names to blockchain and non-blockchain resources, like Ethereum addresses, IPFS hashes, or website URLs. ENS domains can be bought and sold on secondary markets.',  # noqa: E501
        large_image='https://i.seadn.io/gae/BBj09xD7R4bBtg1lgnAAS9_TfoYXKwMtudlk-0fVljlURaK7BWcARCpkM-1LGNGTAcsGO6V1TgrtmQFvCo8uVYW_QEfASK-9j6Nr?w=500&auto=format',  # noqa: E501
        floor_price=FVal(0.00098),
    ),
)

TEST_NFT_YABIR_ETH = NFT(
    token_identifier='_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041',  # noqa: E501
    background_color=None,
    image_url='https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg',
    name='yabir.eth',
    external_link='https://app.ens.domains/name/yabir.eth',
    permalink='https://opensea.io/assets/ethereum/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/26612040215479394739615825115912800930061094786769410446114278812336794170041',  # noqa: E501
    price_eth=FVal(0.00098),
    price_usd=FVal(1.2379458),
    collection=Collection(
        name='ENS: Ethereum Name Service',
        banner_image=None,
        description='Ethereum Name Service (ENS) domains are secure domain names for the decentralized world. ENS domains provide a way for users to map human readable names to blockchain and non-blockchain resources, like Ethereum addresses, IPFS hashes, or website URLs. ENS domains can be bought and sold on secondary markets.',  # noqa: E501
        large_image='https://i.seadn.io/gae/BBj09xD7R4bBtg1lgnAAS9_TfoYXKwMtudlk-0fVljlURaK7BWcARCpkM-1LGNGTAcsGO6V1TgrtmQFvCo8uVYW_QEfASK-9j6Nr?w=500&auto=format',  # noqa: E501
        floor_price=FVal(0.00098),
    ),
)


@requires_env([TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
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


@requires_env([TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
@pytest.mark.vcr()
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


@requires_env([TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
@pytest.mark.vcr()
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
    assert any(expected_id in nft_id for nft_id in ids_1)
    assert any(expected_id in nft_id for nft_id in ids_2)
    all_ids = ids_1 + ids_2
    set_of_ids = set(all_ids)
    assert len(all_ids) == len(set_of_ids)


@requires_env([TestEnvironment.STANDARD, TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4, TEST_ACC5, TEST_ACC6]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts', 'uniswap']])
def test_nft_balances_and_prices(rotkehlchen_api_server):
    """Check that nfts balances return the expected fields. Also check nft prices"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False})
    result = assert_proper_response_with_result(response)
    assert result['entries'] == [], 'nothing should be returned with ignore_cache=False until nfts are queried'  # noqa: E501
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': True})
    result_ignored_cache = assert_proper_response_with_result(response)
    assert result_ignored_cache['entries_found'] == 4
    for nft_balance in result_ignored_cache['entries']:
        if nft_balance['id'] == NFT_ID_FOR_TEST_ACC4:
            assert nft_balance['name'] == 'yabir.eth'
            assert nft_balance['collection_name'] == 'ENS: Ethereum Name Service'
            assert nft_balance['is_lp'] is False
            assert FVal(nft_balance['usd_price']) > ZERO
        elif nft_balance['id'] == NFT_ID_FOR_TEST_ACC5:
            assert nft_balance['name'] == 'nebolax.eth'
            assert nft_balance['collection_name'] == 'ENS: Ethereum Name Service'
            assert nft_balance['is_lp'] is False
            assert FVal(nft_balance['usd_price']) > ZERO
        elif nft_balance['id'] == NFT_ID_FOR_TEST_ACC6_1:
            assert nft_balance['name'] == 'Uniswap - 0.3% - USDT/WETH - 224.56<>2445.5'
            assert nft_balance['collection_name'] == 'Uniswap V3 Positions'
            assert nft_balance['is_lp'] is True
            assert FVal(nft_balance['usd_price']) > ZERO
        elif nft_balance['id'] == NFT_ID_FOR_TEST_ACC6_2:
            assert nft_balance['name'] == 'Uniswap - 0.3% - SHIB/WETH - 79010000<>166260000'
            assert nft_balance['collection_name'] == 'Uniswap V3 Positions'
            assert nft_balance['is_lp'] is True
            assert FVal(nft_balance['usd_price']) > ZERO
        else:
            raise AssertionError('NFT has to be one of the expected')

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False})
    result = assert_proper_response_with_result(response)
    assert result == result_ignored_cache, 'after querying nfts should be returned even with ignore_cache=False'  # noqa: E501

    # Check that search by name works
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'name': 'nebolax'})
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 1
    assert result['entries'][0]['id'] == NFT_ID_FOR_TEST_ACC5

    # check that pagination works as expected
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={
        'async_query': False,
        'ignore_cache': False,
        'ignored_assets_handling': 'exclude',
        'limit': 2,
        'offset': 2,
    })
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 4
    assert result['entries_total'] == 4

    # ignore an nft
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredassetsresource',
        ),
        json={'assets': [NFT_ID_FOR_TEST_ACC4, NFT_ID_FOR_TEST_ACC6_2]},
    )

    # Make sure that ignoring cache doesn't remove any NFTs from the app
    response_with_cache = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'ignored_assets_handling': 'none'})
    response_ignored_cache = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': True, 'ignored_assets_handling': 'none'})
    result_with_cache = assert_proper_response_with_result(response_with_cache)
    result_ignored_cache = assert_proper_response_with_result(response_ignored_cache)
    assert result_with_cache == result_ignored_cache

    # Check that filtering ignored nfts works
    assert result_with_cache['entries_found'] == 4
    assert result_with_cache['entries_total'] == 4
    assert {entry['id'] for entry in result_with_cache['entries']} == {
        NFT_ID_FOR_TEST_ACC4,
        NFT_ID_FOR_TEST_ACC5,
        NFT_ID_FOR_TEST_ACC6_1,
        NFT_ID_FOR_TEST_ACC6_2,
    }

    # Make sure that after invalidating NFTs cache ignored NFTs remain ignored
    response_with_cache = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'ignored_assets_handling': 'exclude'})
    result_with_cache = assert_proper_response_with_result(response_with_cache)
    response_ignored_cache = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'ignored_assets_handling': 'exclude'})
    result_ignored_cache = assert_proper_response_with_result(response_ignored_cache)
    assert result_with_cache == result_ignored_cache

    # Check that the response is correct
    assert result_with_cache['entries_found'] == 2
    assert result_with_cache['entries_total'] == 4
    expected_nfts_without_ignored = {NFT_ID_FOR_TEST_ACC5, NFT_ID_FOR_TEST_ACC6_1}
    assert {entry['id'] for entry in result_with_cache['entries']} == expected_nfts_without_ignored  # noqa: E501
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'ignored_assets_handling': 'show only'})
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 2
    assert result['entries_total'] == 4
    assert {entry['id'] for entry in result['entries']} == {
        NFT_ID_FOR_TEST_ACC4,
        NFT_ID_FOR_TEST_ACC6_2,
    }

    response = requests.post(api_url_for(
        rotkehlchen_api_server,
        'nftspricesresource',
    ))
    result = assert_proper_response_with_result(response)
    for nft in result:
        if nft['asset'] == NFT_ID_FOR_TEST_ACC5:
            expected_result = {
                'asset': NFT_ID_FOR_TEST_ACC5,
                'manually_input': False,
                'price_asset': 'ETH',
            }
            price = nft.pop('price_in_asset')
            price_usd = nft.pop('usd_price')
            assert expected_result == nft
            assert FVal(price) > 0
            assert FVal(price_usd) > 0

    # check that getting information from the database works as expected
    response = requests.post(api_url_for(
        rotkehlchen_api_server,
        'assetsmappingresource',
    ), json={
        'identifiers': [NFT_ID_FOR_TEST_ACC4],
    })
    result = assert_proper_response_with_result(response)['assets'][NFT_ID_FOR_TEST_ACC4]
    assert result == {
        'name': 'yabir.eth',
        'asset_type': 'nft',
        'image_url': 'https://openseauserdata.com/files/238f73fa1bbea518eec64f9c9d5ed7fe.svg',
        'collection_name': 'ENS: Ethereum Name Service',
    }


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4, TEST_ACC5]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_edit_delete_nft(rotkehlchen_api_server):
    """Check that ignoring NFTs work as expected"""
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    nft_map = {
        TEST_ACC4: [TEST_NFT_YABIR_ETH],
        TEST_ACC5: [TEST_NFT_NEBOLAX_ETH],
    }

    def mock_get_all_nft_data(addresses, **kwargs):  # pylint: disable=unused-argument
        return nft_map, sum([len(x) for x in nft_map.values()])

    get_all_nft_data_patch = patch(
        'rotkehlchen.chain.ethereum.modules.nft.nfts.Nfts._get_all_nft_data',
        side_effect=mock_get_all_nft_data,
    )

    with get_all_nft_data_patch:
        # First fetch 2 nfts
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'nftsbalanceresource',
            ),
            json={'async_query': False, 'ignore_cache': True},
        )
        result = assert_proper_response_with_result(response)
        assert result['entries_found'] == 2
        assert result['entries'][1]['price_in_asset'] == '0.0012'
        assert result['entries'][1]['image_url'] == 'https://openseauserdata.com/files/8fd18b22e4c81aff3998956e7a712d93.svg'  # noqa: E501

        # Also check that db was updated properly
        with db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM nfts').fetchone()[0] == 2
            price_and_image_url_in_db = cursor.execute(
                'SELECT last_price, image_url FROM nfts WHERE owner_address=?',
                (TEST_ACC5,),
            ).fetchall()
            assert len(price_and_image_url_in_db) == 1
            assert price_and_image_url_in_db[0][0] == '0.0012'
            assert price_and_image_url_in_db[0][1] == 'https://openseauserdata.com/files/8fd18b22e4c81aff3998956e7a712d93.svg'  # noqa: E501

        # Change one of the NFTs' price and image_url in the response and make sure these changes
        # are reflected in the response and the db
        nft_map[TEST_ACC5][0] = NFT(
            token_identifier='_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_73552724610198397480670284492690114609730214421511097849210414928326607694469',  # noqa: E501
            background_color=None,
            image_url='https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg',
            name='nebolax.eth',
            external_link='https://app.ens.domains/name/nebolax.eth',
            permalink='https://opensea.io/assets/ethereum/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/73552724610198397480670284492690114609730214421511097849210414928326607694469',  # noqa: E501
            price_eth=FVal(0.5),
            price_usd=FVal(1.2379458),
            collection=Collection(
                name='ENS: Ethereum Name Service',
                banner_image=None,
                description='Ethereum Name Service (ENS) domains are secure domain names for the decentralized world. ENS domains provide a way for users to map human readable names to blockchain and non-blockchain resources, like Ethereum addresses, IPFS hashes, or website URLs. ENS domains can be bought and sold on secondary markets.',  # noqa: E501
                large_image='https://i.seadn.io/gae/BBj09xD7R4bBtg1lgnAAS9_TfoYXKwMtudlk-0fVljlURaK7BWcARCpkM-1LGNGTAcsGO6V1TgrtmQFvCo8uVYW_QEfASK-9j6Nr?w=500&auto=format',  # noqa: E501
                floor_price=FVal(0.00098),
            ),
        )
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'nftsbalanceresource',
            ),
            json={'async_query': False, 'ignore_cache': True},
        )
        result = assert_proper_response_with_result(response)
        assert result['entries_found'] == 2
        assert result['entries'][1]['price_in_asset'] == '0.5'
        assert result['entries'][1]['image_url'] == 'https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg'  # noqa: E501

        # Also check that db was updated properly
        with db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM nfts').fetchone()[0] == 2
            price_and_image_url_in_db = cursor.execute(
                'SELECT last_price, image_url FROM nfts WHERE owner_address=?',
                (TEST_ACC5,),
            ).fetchall()
            assert len(price_and_image_url_in_db) == 1
            assert price_and_image_url_in_db[0][0] == '0.5'
            assert price_and_image_url_in_db[0][1] == 'https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg'  # noqa: E501

        # Remove one of the accounts with an NFT from the response
        # and check that response and db are the expected ones.
        del nft_map[TEST_ACC5]

        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'nftsbalanceresource',
            ),
            json={'async_query': False, 'ignore_cache': True},
        )
        result = assert_proper_response_with_result(response)
        assert result['entries_found'] == 1 and result['entries'][0]['name'] == 'yabir.eth'

        # Also check that db was updated properly
        with db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM nfts').fetchone()[0] == 1
            assert cursor.execute('SELECT COUNT(*) FROM nfts WHERE owner_address=?', (TEST_ACC5,)).fetchone()[0] == 0  # noqa: E501


@requires_env([TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
@pytest.mark.parametrize('endpoint', ['nftsbalanceresource', 'nftsresource'])
def test_nfts_ignoring_works(rotkehlchen_api_server, endpoint):
    """Check that ignoring NFTs work as expected"""
    def mock_get_all_nft_data(addresses, **kwargs):  # pylint: disable=unused-argument
        nft_map = {
            '0xc37b40ABdB939635068d3c5f13E7faF686F03B65': [TEST_NFT_YABIR_ETH],
        }
        return nft_map, 1

    get_all_nft_data_patch = patch('rotkehlchen.chain.ethereum.modules.nft.nfts.Nfts._get_all_nft_data', side_effect=mock_get_all_nft_data)  # noqa: E501

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
            assert result == {
                'entries': [],
                'entries_found': 0,
                'entries_total': 0,
                'total_usd_value': '0',
            }

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
            json={'async_query': False, 'ignore_cache': True},
        )
        result = assert_proper_response_with_result(response)
        if endpoint == 'nftsresource':
            all_nfts_ids = {nft['token_identifier'] for nft in result['addresses'][TEST_ACC4]}
        else:
            all_nfts_ids = {nft['id'] for nft in result['entries']}
        assert NFT_ID_FOR_TEST_ACC4 in all_nfts_ids


@requires_env([TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
@pytest.mark.parametrize('ethereum_accounts', [['0x7277F7849966426d345D8F6B9AFD1d3d89183083']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_no_price(rotkehlchen_api_server):
    """Test for nft with no price and that query works fine"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    nft_module = rotki.chains_aggregator.get_module('nfts')

    def mock_session_get(url, params, timeout):  # pylint: disable=unused-argument
        if 'assets' in url:
            response = """
        {"assets":[{
        "animation_original_url": "https://resources.smarttokenlabs.com/devcon6/Comp_ETH.mp4",
        "animation_url": "https://openseauserdata.com/files/8ce39e632261c0d61bb122c314f49ef7.mp4",
        "asset_contract": {
            "address": "0x7522dc5a357891b4daec194e285551ea5ea66d09",
            "asset_contract_type": "non-fungible",
            "buyer_fee_basis_points": 0,
            "created_date": "2022-10-14T22:45:02.644744",
            "default_to_fiat": false,
            "description": "bla bla",
            "dev_buyer_fee_basis_points": 0,
            "dev_seller_fee_basis_points": 0,
            "external_link": "https://devcon-vi.attest.tickets/",
            "image_url": "https://i.seadn.io/gae/ED1IC2aJj9RlHheixOlc3CH_oV4I1egLchaDAkqccx5EEC-foJcG0CUZNt9QhkIyLKOS1ZDqvkhPQcxSyvLDCWeytSv-Flv8acRM8g?w=500&auto=format",
            "name": "Unidentified contract",
            "nft_version": null,
            "only_proxied_transfers": false,
            "opensea_buyer_fee_basis_points": 0,
            "opensea_seller_fee_basis_points": 250,
            "opensea_version": null,
            "owner": null,
            "payout_address": null,
            "schema_name": "ERC721",
            "seller_fee_basis_points": 250,
            "symbol": "",
            "total_supply": null
        },
        "background_color": null,
        "collection": {
            "banner_image_url": null,
            "chat_url": null,
            "created_date": "2022-10-15T01:30:47.057694+00:00",
            "default_to_fiat": false,
            "description": "bla bla",
            "dev_buyer_fee_basis_points": "0",
            "dev_seller_fee_basis_points": "0",
            "discord_url": null,
            "display_data": {"card_display_style": "contain", "images": []},
            "external_url": "https://devcon-vi.attest.tickets/",
            "featured": false,
            "featured_image_url": null,
            "fees": {"opensea_fees": {"0x0000a26b00c1f0df003000390027140000faa719": 250}, "seller_fees": {}},
            "hidden": false,
            "image_url": "https://i.seadn.io/gae/ED1IC2aJj9RlHheixOlc3CH_oV4I1egLchaDAkqccx5EEC-foJcG0CUZNt9QhkIyLKOS1ZDqvkhPQcxSyvLDCWeytSv-Flv8acRM8g?w=500&auto=format",
            "instagram_username": null,
            "is_nsfw": false,
            "is_rarity_enabled": false,
            "is_subject_to_whitelist": false,
            "large_image_url": "https://i.seadn.io/gae/ED1IC2aJj9RlHheixOlc3CH_oV4I1egLchaDAkqccx5EEC-foJcG0CUZNt9QhkIyLKOS1ZDqvkhPQcxSyvLDCWeytSv-Flv8acRM8g?w=500&auto=format",
            "medium_username": null,
            "name": "Devcon VI Souvenir V4",
            "only_proxied_transfers": false,
            "opensea_buyer_fee_basis_points": "0",
            "opensea_seller_fee_basis_points": "250",
            "payout_address": null,
            "require_email": false,
            "safelist_request_status": "not_requested",
            "short_description": null,
            "slug": "devcon-vi-souvenir-v4",
            "telegram_url": null,
            "twitter_username": null,
            "wiki_url": null
        },
        "creator": {
            "address": "0xff3efd475907f5c6dc173fe42c2dd3a58ef740bf",
            "config": "",
            "profile_img_url": "https://storage.googleapis.com/opensea-static/opensea-profile/10.png",
            "user": {"username": null}
        },
        "decimals": null,
        "description": "bla bla",
        "external_link": null,
        "id": 724471261,
        "image_original_url": "https://resources.smarttokenlabs.com/devcon6/ETH.webp",
        "image_preview_url": "https://i.seadn.io/gae/-N3ctyPYwIF0s-pShI-Zcg96KJr7dYG05KyFtI25WG0yIZeOpBxjAIIUBiBmHcbviAFkY57Xfo0-MRaonHHx4a53LS-q2yOoEwzF?w=500&auto=format",
        "image_thumbnail_url": "https://i.seadn.io/gae/-N3ctyPYwIF0s-pShI-Zcg96KJr7dYG05KyFtI25WG0yIZeOpBxjAIIUBiBmHcbviAFkY57Xfo0-MRaonHHx4a53LS-q2yOoEwzF?w=500&auto=format",
        "image_url": "https://i.seadn.io/gae/-N3ctyPYwIF0s-pShI-Zcg96KJr7dYG05KyFtI25WG0yIZeOpBxjAIIUBiBmHcbviAFkY57Xfo0-MRaonHHx4a53LS-q2yOoEwzF?w=500&auto=format",
        "is_nsfw": false,
        "is_presale": false,
        "last_sale": null,
        "listing_date": null,
        "name": "Devcon VI Souvenir",
        "num_sales": 0,
        "owner": {
            "address": "0x0000000000000000000000000000000000000000",
            "config": "",
            "profile_img_url": "https://storage.googleapis.com/opensea-static/opensea-profile/1.png",
            "user": {"username": "NullAddress"}
        },
        "permalink": "https://opensea.io/assets/ethereum/0x7522dc5a357891b4daec194e285551ea5ea66d09/336510496872176433120578",
        "rarity_data": null,
        "seaport_sell_orders": null,
        "supports_wyvern": true,
        "token_id": "336510496872176433120578",
        "token_metadata": "https://resources.smarttokenlabs.com/1/0x7522dc5a357891b4daec194e285551ea5ea66d09/336510496872176433120578",
        "top_bid": null,
        "traits": [],
        "transfer_fee": null,
        "transfer_fee_payment_token": null}]}
        """  # noqa: E501
        elif 'collections' in url:
            response = """[{
                "primary_asset_contracts": [1, 2, 3],
                "name": "Devcon VI Souvenir V4",
                "slug": "devconsouvenir",
                "banner_image_url": "url",
                "large_image_url": "url",
                "description": "bla bla"
            }]"""
        elif '/stats' in url:
            response = """{
                "stats": {
                    "floor_price": null
                }
            }"""
        else:
            raise AssertionError(f'Unexpected url {url} queried in test')

        return MockResponse(200, response)

    patched_opensea = patch.object(nft_module.opensea.session, 'get', wraps=mock_session_get)
    with patched_opensea:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'nftsbalanceresource',
            ), json={'ignore_cache': True},
        )
    result = assert_proper_response_with_result(response)
    assert result == {
        'entries': [{
            'collection_name': 'Devcon VI Souvenir V4',
            'id': '_nft_0x7522dc5a357891b4daec194e285551ea5ea66d09_336510496872176433120578',
            'image_url': 'https://i.seadn.io/gae/-N3ctyPYwIF0s-pShI-Zcg96KJr7dYG05KyFtI25WG0yIZeOpBxjAIIUBiBmHcbviAFkY57Xfo0-MRaonHHx4a53LS-q2yOoEwzF?w=500&auto=format',  # noqa: E501
            'is_lp': False,
            'manually_input': False,
            'name': 'Devcon VI Souvenir',
            'price_asset': 'ETH',
            'price_in_asset': '0',
            'usd_price': '0.0'}],
        'entries_found': 1,
        'entries_total': 1,
        'total_usd_value': '0.0',
    }


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4, TEST_ACC5, TEST_ACC6]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts', 'uniswap']])
def test_lp_nfts_filtering(rotkehlchen_api_server):
    """Assert that filtering by the lp property for NFTs works properly on all the endpoints that
    allow it
    """
    def mock_get_all_nft_data(_addresses, **_kwargs) -> tuple[dict[str, Any], int]:
        data = {
            '0x4bBa290826C253BD854121346c370a9886d1bC26': [TEST_NFT_NEBOLAX_ETH],
            '0xc37b40ABdB939635068d3c5f13E7faF686F03B65': [TEST_NFT_YABIR_ETH],
            '0x3e649c5Eac6BBEE8a4F2A2945b50d8e582faB3bf': [
                NFT(
                    token_identifier='_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_360762',
                    background_color=None,
                    image_url='https://openseauserdata.com/files/99b67e38e2d1abc16d6d843f478b5224.svg',  # noqa: E501
                    name='Uniswap - 0.3% - SHIB/WETH - 79010000<>166260000',
                    external_link=None,
                    permalink='https://opensea.io/assets/ethereum/0xc36442b4a4522e871399cd717abdd847ab11fe88/360762',  # noqa: E501
                    price_eth=ZERO,
                    price_usd=ZERO,
                    collection=Collection(
                        name='Uniswap V3 Positions',
                        banner_image='https://i.seadn.io/gae/Xq98abLTjlFfzdIxsXNL0sVE2W-3FGcJ2TFUkphz9dh9wEH4rcUesMhE7RzEh_ivPCdL5KxkNVfyE5gb870OgqOLQnBP6sIL54-G0A?w=500&auto=format',  # noqa: E501
                        description='',
                        large_image='https://i.seadn.io/gae/cnVFmcBCIreYJxfaZ2ba62kEdC9ocuP7vawwcfZx9QIOVNlisuJTV2f19D48hg2NSUxPFX6peemTKaYshJvs-vIcy_3Kv3nCiF7t9g?w=500&auto=format',  # noqa: E501
                        floor_price=None,
                    ),
                ),
                NFT(
                    token_identifier='_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_360680',
                    background_color=None,
                    image_url='https://openseauserdata.com/files/53f418fceab543a174d22efd0a55782c.svg',  # noqa: E501
                    name='Uniswap - 0.3% - USDT/WETH - 224.56<>2445.5',
                    external_link=None,
                    permalink='https://opensea.io/assets/ethereum/0xc36442b4a4522e871399cd717abdd847ab11fe88/360680',  # noqa: E501
                    price_eth=ZERO,
                    price_usd=ZERO,
                    collection=Collection(
                        name='Uniswap V3 Positions',
                        banner_image='https://i.seadn.io/gae/Xq98abLTjlFfzdIxsXNL0sVE2W-3FGcJ2TFUkphz9dh9wEH4rcUesMhE7RzEh_ivPCdL5KxkNVfyE5gb870OgqOLQnBP6sIL54-G0A?w=500&auto=format',  # noqa: E501
                        description='',
                        large_image='https://i.seadn.io/gae/cnVFmcBCIreYJxfaZ2ba62kEdC9ocuP7vawwcfZx9QIOVNlisuJTV2f19D48hg2NSUxPFX6peemTKaYshJvs-vIcy_3Kv3nCiF7t9g?w=500&auto=format',  # noqa: E501
                        floor_price=None,
                    ),
                ),
            ],
        }
        return data, 4

    def mock_uniswap_v3_balances(*_args, **_kwargs) -> dict[str, Any]:
        return {
            '0x3e649c5Eac6BBEE8a4F2A2945b50d8e582faB3bf': [
                NFTLiquidityPool(
                    address=string_to_evm_address('0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36'),
                    assets=[
                        LiquidityPoolAsset(
                            token=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),  # noqa: E501
                            total_amount=FVal(467.1438481374891080028754879),
                            user_balance=Balance(
                                amount=FVal(0.07634689899681738268929722925),
                                usd_value=FVal(0.1145203484952260740339458439),
                            ),
                            usd_price=Price(FVal(1.5)),
                        ), LiquidityPoolAsset(
                            token=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),  # noqa: E501
                            total_amount=FVal(590091.4573701435329438497875),
                            user_balance=Balance(
                                amount=FVal(197.9498109045197253831082955),
                                usd_value=FVal(296.9247163567795880746624432),
                            ),
                            usd_price=Price(FVal(1.5)),
                        ),
                    ],
                    total_supply=None,
                    user_balance=Balance(
                        amount=ZERO,
                        usd_value=FVal(297.0392367052748141486963890),
                    ),
                    nft_id='_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_360680',
                    price_range=(
                        FVal(0.0004089111961461131970577658069),
                        FVal(0.004453201773423214426045068107),
                    ),
                ),
                NFTLiquidityPool(
                    address=string_to_evm_address('0x2F62f2B4c5fcd7570a709DeC05D68EA19c82A9ec'),
                    assets=[
                        LiquidityPoolAsset(
                            token=EvmToken('eip155:1/erc20:0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE'),  # noqa: E501
                            total_amount=FVal(7434412870.4299540940086804),
                            user_balance=Balance(
                                amount=FVal(14993034.44120264275215351374),
                                usd_value=FVal(22489551.66180396412823027061),
                            ),
                            usd_price=Price(FVal(1.5)),
                        ), LiquidityPoolAsset(
                            token=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),  # noqa: E501
                            total_amount=FVal(54.08313355138617618618670289),
                            user_balance=Balance(
                                amount=FVal(0.04035273849436677000793717497),
                                usd_value=FVal(0.06052910774155015501190576246),
                            ),
                            usd_price=Price(FVal(1.5)),
                        ),
                    ],
                    total_supply=None,
                    user_balance=Balance(
                        amount=ZERO,
                        usd_value=FVal(22489551.72233307186978042562),
                    ),
                    nft_id='_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_360762',
                    price_range=(
                        FVal(79010456.35648359278851139208),
                        FVal(166258366.8407051322948007978),
                    ),
                ),
            ]}

    get_all_nft_data_patch = patch('rotkehlchen.chain.ethereum.modules.nft.nfts.Nfts._get_all_nft_data', side_effect=mock_get_all_nft_data)  # noqa: E501
    get_v3_balances_patch = patch('rotkehlchen.chain.ethereum.modules.uniswap.Uniswap.get_v3_balances', side_effect=mock_uniswap_v3_balances)  # noqa: E501

    with get_all_nft_data_patch, get_v3_balances_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'nftsbalanceresource',
            ),
            json={'async_query': False, 'ignore_cache': True},
        )
        result = assert_proper_response_with_result(response)
        assert result['entries_found'] == 4

    # test that only lp works
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'nftsbalanceresource',
        ),
        json={
            'async_query': False,
            'ignore_cache': False,
            'lps_handling': NftLpHandling.ONLY_LPS.serialize(),
        },
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 2
    for entry in result['entries']:
        assert entry['is_lp'] is True

    # Test that non lp + filter works
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'nftsbalanceresource',
        ),
        json={
            'async_query': False,
            'ignore_cache': False,
            'lps_handling': NftLpHandling.EXCLUDE_LPS.serialize(),
            'name': 'yabir',
        },
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 1

    # test the handling in the prices endpoint
    response = requests.post(api_url_for(
        rotkehlchen_api_server,
        'nftspricesresource',
    ), json={'lps_handling': NftLpHandling.ONLY_LPS.serialize()})
    result = assert_proper_response_with_result(response)
    for nft in result:
        assert nft['asset'] in (NFT_ID_FOR_TEST_ACC6_1, NFT_ID_FOR_TEST_ACC6_2)

    response = requests.post(api_url_for(
        rotkehlchen_api_server,
        'nftspricesresource',
    ), json={'lps_handling': NftLpHandling.EXCLUDE_LPS.serialize()})
    result = assert_proper_response_with_result(response)
    assert len(result) == 2
    for nft in result:
        assert nft['asset'] not in (NFT_ID_FOR_TEST_ACC6_1, NFT_ID_FOR_TEST_ACC6_2)

    response = requests.post(api_url_for(
        rotkehlchen_api_server,
        'nftspricesresource',
    ))
    result = assert_proper_response_with_result(response)
    assert len(result) == 4


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4, TEST_ACC5]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_customized_queried_addresses(rotkehlchen_api_server):
    """
    Test that if queried addresses are customized for nfts module, then from /nfts/balances only
    NFTs of those addresses are returned"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def mock_get_all_nft_data(_addresses, **_kwargs) -> tuple[dict[str, Any], int]:
        data = {
            TEST_ACC5: [TEST_NFT_NEBOLAX_ETH],
            TEST_ACC4: [TEST_NFT_YABIR_ETH],
        }
        return data, 2

    get_all_nft_data_patch = patch('rotkehlchen.chain.ethereum.modules.nft.nfts.Nfts._get_all_nft_data', side_effect=mock_get_all_nft_data)  # noqa: E501

    with get_all_nft_data_patch:
        response = requests.get(  # Populate the NFTs
            api_url_for(
                rotkehlchen_api_server,
                'nftsbalanceresource',
            ),
            json={'async_query': False, 'ignore_cache': True},
        )
        result = assert_proper_response_with_result(response)
        assert result['entries_found'] == 2

    # Make NFTs queried for only one of the addresses
    QueriedAddresses(rotki.data.db).add_queried_address_for_module(
        module='nfts',
        address=TEST_ACC5,
    )
    response = requests.get(  # Now we should get the NFTs only for TEST_ACC5 address
        api_url_for(
            rotkehlchen_api_server,
            'nftsbalanceresource',
        ),
        json={'async_query': False, 'ignore_cache': False},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 1 and result['entries'][0]['name'] == TEST_NFT_NEBOLAX_ETH.name  # noqa: E501
