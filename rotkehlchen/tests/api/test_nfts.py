import warnings as test_warnings
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.ethereum.modules.nft.constants import FREE_NFT_LIMIT
from rotkehlchen.chain.evm.types import ChecksumEvmAddress, string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.externalapis.opensea import NFT, Collection
from rotkehlchen.fval import FVal
from rotkehlchen.tests.conftest import TestEnvironment, requires_env
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.mock import MockResponse

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

TEST_ACC1: Final = string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12')  # lefteris.eth # noqa: E501
TEST_ACC2: Final = string_to_evm_address('0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF')
TEST_ACC3: Final = string_to_evm_address('0xC21A5ee89D306353e065a6dd5779470DE395DBaC')
TEST_ACC4: Final = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')  # yabir.eth, gashawk nft # noqa: E501
TEST_ACC5: Final = string_to_evm_address('0x4bBa290826C253BD854121346c370a9886d1bC26')  # nebolax.eth # noqa: E501
TEST_ACC6: Final = string_to_evm_address('0x3e649c5Eac6BBEE8a4F2A2945b50d8e582faB3bf')  # contains uniswap-v3 nft # noqa: E501
NFT_ID_FOR_TEST_ACC4 = '_nft_0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85_26612040215479394739615825115912800930061094786769410446114278812336794170041'  # noqa: E501
NFT_ID_FOR_TEST_ACC4_2 = '_nft_0xfd9d8036F899ed5a9fD8cac7968E5F24D3db2A64_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # noqa: E501
NFT_ID_FOR_TEST_ACC5 = '_nft_0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85_73552724610198397480670284492690114609730214421511097849210414928326607694469'  # noqa: E501
NFT_ID_FOR_TEST_ACC6_2 = '_nft_0xC36442b4a4522E871399CD717aBDD847Ab11FE88_360762'

TEST_NFT_NEBOLAX_ETH = NFT(
    token_identifier='_nft_0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85_73552724610198397480670284492690114609730214421511097849210414928326607694469',
    background_color=None,
    image_url='https://openseauserdata.com/files/8fd18b22e4c81aff3998956e7a712d93.svg',
    name='nebolax.eth',
    external_link='https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/73552724610198397480670284492690114609730214421511097849210414928326607694469',
    permalink='https://opensea.io/assets/ethereum/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/73552724610198397480670284492690114609730214421511097849210414928326607694469',
    price_in_asset=FVal(0.0012),
    price_asset=A_ETH,
    price_usd=FVal(1.2379458),
    collection=Collection(
        name='ENS: Ethereum Name Service',
        banner_image=None,
        description='Ethereum Name Service (ENS) domains are secure domain names for the decentralized world. ENS domains provide a way for users to map human readable names to blockchain and non-blockchain resources, like Ethereum addresses, IPFS hashes, or website URLs. ENS domains can be bought and sold on secondary markets.',  # noqa: E501
        large_image='https://i.seadn.io/gae/BBj09xD7R4bBtg1lgnAAS9_TfoYXKwMtudlk-0fVljlURaK7BWcARCpkM-1LGNGTAcsGO6V1TgrtmQFvCo8uVYW_QEfASK-9j6Nr?w=500&auto=format',
        floor_price=FVal(0.00098),
        floor_price_asset=A_ETH,
    ),
)

TEST_NFT_YABIR_ETH = NFT(
    token_identifier='_nft_0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85_26612040215479394739615825115912800930061094786769410446114278812336794170041',
    background_color=None,
    image_url='https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg',
    name='yabir.eth',
    external_link='https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/26612040215479394739615825115912800930061094786769410446114278812336794170041',
    permalink='https://opensea.io/assets/ethereum/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/26612040215479394739615825115912800930061094786769410446114278812336794170041',
    price_in_asset=FVal(0.00098),
    price_asset=A_ETH,
    price_usd=FVal(1.2379458),
    collection=Collection(
        name='ENS: Ethereum Name Service',
        banner_image=None,
        description='Ethereum Name Service (ENS) domains are secure domain names for the decentralized world. ENS domains provide a way for users to map human readable names to blockchain and non-blockchain resources, like Ethereum addresses, IPFS hashes, or website URLs. ENS domains can be bought and sold on secondary markets.',  # noqa: E501
        large_image='https://i.seadn.io/gae/BBj09xD7R4bBtg1lgnAAS9_TfoYXKwMtudlk-0fVljlURaK7BWcARCpkM-1LGNGTAcsGO6V1TgrtmQFvCo8uVYW_QEfASK-9j6Nr?w=500&auto=format',
        floor_price=FVal(0.00098),
        floor_price_asset=A_ETH,
    ),
)


@pytest.mark.vcr(
    filter_query_parameters=['apikey'], filter_headers=['X-API-KEY'],
)
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_query(rotkehlchen_api_server: 'APIServer', start_with_valid_premium: bool) -> None:
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsresource',
    ), json={'async_query': True})
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=60)
    assert outcome['message'] == ''
    result = outcome['result']

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
        if entry['token_identifier'] == '_nft_0xc3f733ca98E0daD0386979Eb96fb1722A1A05E69_129':
            assert entry['name'] == 'MoonCat #129: 0x0082206dcb'
            assert entry['external_link'] == 'https://api.mooncat.community/traits/129'
            assert 'image_url' in entry
            assert FVal(entry['price_in_asset']) > ZERO
            assert FVal(entry['price_usd']) > ZERO
            assert entry['collection']['name'] == 'MoonCats'
            assert entry['collection']['banner_image'].startswith('https://')
            assert isinstance(entry['collection']['description'], str)
            assert entry['collection']['large_image'].startswith('https://')
            nft_found = True
            break

    assert nft_found, 'Could not find and verify the test NFT'


@requires_env([TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_query_after_account_add(rotkehlchen_api_server: 'APIServer') -> None:
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
    result = assert_proper_sync_response_with_result(response)

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
    result = assert_proper_sync_response_with_result(response)
    assert TEST_ACC1 in result['addresses']
    assert TEST_ACC2 in result['addresses']


@requires_env([TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC2, TEST_ACC3]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_ids_are_unique(rotkehlchen_api_server: 'APIServer') -> None:
    """Check that if two accounts hold the same semi-fungible token we don't have duplicate ids"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsresource',
    ), json={'async_query': False})

    result = assert_proper_sync_response_with_result(response)
    # get the ids from the query result
    ids_1 = [nft['token_identifier'] for nft in result['addresses'][TEST_ACC2]]
    ids_2 = [nft['token_identifier'] for nft in result['addresses'][TEST_ACC3]]
    # Check that two possible duplicates are between the NFT ids
    expected_id = '_nft_0xFAFf15C6cDAca61a4F87D329689293E07c98f578_1'
    assert any(expected_id in nft_id for nft_id in ids_1)
    assert any(expected_id in nft_id for nft_id in ids_2)
    all_ids = ids_1 + ids_2
    set_of_ids = set(all_ids)
    assert len(all_ids) == len(set_of_ids)


@requires_env([TestEnvironment.STANDARD, TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4, TEST_ACC5, TEST_ACC6]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_balances_and_prices(rotkehlchen_api_server: 'APIServer') -> None:
    """Check that nfts balances return the expected fields. Also check nft prices"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False})
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'] == [], 'nothing should be returned with ignore_cache=False until nfts are queried'  # noqa: E501
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': True})
    result_ignored_cache = assert_proper_sync_response_with_result(response)
    assert result_ignored_cache['entries_found'] == 3
    for nft_balance in result_ignored_cache['entries']:
        if nft_balance['id'] == NFT_ID_FOR_TEST_ACC4:
            assert nft_balance['name'] == 'yabir.eth'
            assert nft_balance['collection_name'] == 'ENS: Ethereum Name Service'
            assert nft_balance['is_lp'] is False
            assert FVal(nft_balance['price']) > ZERO
        elif nft_balance['id'] == NFT_ID_FOR_TEST_ACC4_2:
            assert nft_balance['name'] == 'GasHawk Nest NFT'
            assert nft_balance['collection_name'] == 'GasHawk NFTs'
            assert nft_balance['is_lp'] is False
            assert FVal(nft_balance['price']) >= ZERO
        elif nft_balance['id'] == NFT_ID_FOR_TEST_ACC5:
            assert nft_balance['name'] == 'nebolax.eth'
            assert nft_balance['collection_name'] == 'ENS: Ethereum Name Service'
            assert nft_balance['is_lp'] is False
            assert FVal(nft_balance['price']) > ZERO
        else:
            raise AssertionError('NFT has to be one of the expected')

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False})
    result = assert_proper_sync_response_with_result(response)
    assert result == result_ignored_cache, 'after querying nfts should be returned even with ignore_cache=False'  # noqa: E501

    # Check that search by name works
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'name': 'nebolax'})
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 3
    assert result['entries_total'] == 3

    # ignore an nft
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredassetsresource',
        ),
        json={'assets': [NFT_ID_FOR_TEST_ACC4, NFT_ID_FOR_TEST_ACC6_2, NFT_ID_FOR_TEST_ACC4_2]},
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
    result_with_cache = assert_proper_sync_response_with_result(response_with_cache)
    result_ignored_cache = assert_proper_sync_response_with_result(response_ignored_cache)
    assert result_with_cache == result_ignored_cache

    # Check that filtering ignored nfts works
    assert result_with_cache['entries_found'] == 3
    assert result_with_cache['entries_total'] == 3
    assert {entry['id'] for entry in result_with_cache['entries']} == {
        NFT_ID_FOR_TEST_ACC4,
        NFT_ID_FOR_TEST_ACC4_2,
        NFT_ID_FOR_TEST_ACC5,
    }

    # Make sure that after invalidating NFTs cache ignored NFTs remain ignored
    response_with_cache = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'ignored_assets_handling': 'exclude'})
    result_with_cache = assert_proper_sync_response_with_result(response_with_cache)
    response_ignored_cache = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'ignored_assets_handling': 'exclude'})
    result_ignored_cache = assert_proper_sync_response_with_result(response_ignored_cache)
    assert result_with_cache == result_ignored_cache

    # Check that the response is correct
    assert result_with_cache['entries_found'] == 1
    assert result_with_cache['entries_total'] == 3
    expected_nfts_without_ignored = {NFT_ID_FOR_TEST_ACC5}
    assert {entry['id'] for entry in result_with_cache['entries']} == expected_nfts_without_ignored
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'ignored_assets_handling': 'show only'})
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 2
    assert result['entries_total'] == 3
    assert {entry['id'] for entry in result['entries']} == {
        NFT_ID_FOR_TEST_ACC4,
        NFT_ID_FOR_TEST_ACC4_2,
    }

    response = requests.post(api_url_for(
        rotkehlchen_api_server,
        'nftspricesresource',
    ))
    result = assert_proper_sync_response_with_result(response)
    for nft in result:
        if nft['asset'] == NFT_ID_FOR_TEST_ACC5:
            expected_result = {
                'asset': NFT_ID_FOR_TEST_ACC5,
                'manually_input': False,
                'price_asset': 'ETH',
            }
            price = nft.pop('price_in_asset')
            price_usd = nft.pop('price')
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
    result = assert_proper_sync_response_with_result(response)['assets'][NFT_ID_FOR_TEST_ACC4]
    assert result == {
        'name': 'yabir.eth',
        'asset_type': 'nft',
        'image_url': 'https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/0x3ad5e1887ef8024efa6d5070ccfda4868783a5343e1089e47fda9b4f7ce4f2b9/image',
        'collection_name': 'ENS: Ethereum Name Service',
    }


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4, TEST_ACC5]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_edit_delete_nft(rotkehlchen_api_server: 'APIServer') -> None:
    """Check that ignoring NFTs work as expected"""
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    nft_map = {
        TEST_ACC4: [TEST_NFT_YABIR_ETH],
        TEST_ACC5: [TEST_NFT_NEBOLAX_ETH],
    }

    def mock_get_all_nft_data(
            addresses: list[ChecksumEvmAddress],
            **kwargs,
        ) -> tuple[dict[ChecksumEvmAddress, list[NFT]], int]:  # pylint: disable=unused-argument
        return nft_map, sum(len(x) for x in nft_map.values())

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
        result = assert_proper_sync_response_with_result(response)
        assert result['entries_found'] == 2
        assert result['entries'][1]['price_in_asset'] == '0.0012'
        assert result['entries'][1]['image_url'] == 'https://openseauserdata.com/files/8fd18b22e4c81aff3998956e7a712d93.svg'

        # Also check that db was updated properly
        with db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM nfts').fetchone()[0] == 2
            price_and_image_url_in_db = cursor.execute(
                'SELECT last_price, image_url FROM nfts WHERE owner_address=?',
                (TEST_ACC5,),
            ).fetchall()
            assert len(price_and_image_url_in_db) == 1
            assert price_and_image_url_in_db[0][0] == '0.0012'
            assert price_and_image_url_in_db[0][1] == 'https://openseauserdata.com/files/8fd18b22e4c81aff3998956e7a712d93.svg'

        # Change one of the NFTs' price and image_url in the response and make sure these changes
        # are reflected in the response and the db
        nft_map[TEST_ACC5][0] = NFT(
            token_identifier='_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_73552724610198397480670284492690114609730214421511097849210414928326607694469',
            background_color=None,
            image_url='https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg',
            name='nebolax.eth',
            external_link='https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/73552724610198397480670284492690114609730214421511097849210414928326607694469',
            permalink='https://opensea.io/assets/ethereum/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/73552724610198397480670284492690114609730214421511097849210414928326607694469',
            price_in_asset=FVal(0.5),
            price_asset=A_ETH,
            price_usd=FVal(1.2379458),
            collection=Collection(
                name='ENS: Ethereum Name Service',
                banner_image=None,
                description='Ethereum Name Service (ENS) domains are secure domain names for the decentralized world. ENS domains provide a way for users to map human readable names to blockchain and non-blockchain resources, like Ethereum addresses, IPFS hashes, or website URLs. ENS domains can be bought and sold on secondary markets.',  # noqa: E501
                large_image='https://i.seadn.io/gae/BBj09xD7R4bBtg1lgnAAS9_TfoYXKwMtudlk-0fVljlURaK7BWcARCpkM-1LGNGTAcsGO6V1TgrtmQFvCo8uVYW_QEfASK-9j6Nr?w=500&auto=format',
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
        result = assert_proper_sync_response_with_result(response)
        assert result['entries_found'] == 2
        assert result['entries'][1]['price_in_asset'] == '0.5'
        assert result['entries'][1]['image_url'] == 'https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg'

        # Also check that db was updated properly
        with db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM nfts').fetchone()[0] == 2
            price_and_image_url_in_db = cursor.execute(
                'SELECT last_price, image_url FROM nfts WHERE owner_address=?',
                (TEST_ACC5,),
            ).fetchall()
            assert len(price_and_image_url_in_db) == 1
            assert price_and_image_url_in_db[0][0] == '0.5'
            assert price_and_image_url_in_db[0][1] == 'https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg'

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
        result = assert_proper_sync_response_with_result(response)
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
def test_nfts_ignoring_works(rotkehlchen_api_server: 'APIServer', endpoint: str):
    """Check that ignoring NFTs work as expected"""
    def mock_get_all_nft_data(
            addresses: list[ChecksumEvmAddress],
            **kwargs,
        ) -> tuple[dict[str, list[NFT]], int]:  # pylint: disable=unused-argument
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
    result = assert_proper_sync_response_with_result(response)
    assert NFT_ID_FOR_TEST_ACC4 in result['successful']

    # query the nfts endpoint and verify that the nft is not present
    with get_all_nft_data_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                endpoint,
            ),
            json={'async_query': False},
        )
        result = assert_proper_sync_response_with_result(response)
        if endpoint == 'nftsresource':
            all_nfts_ids = {nft['token_identifier'] for nft in result['addresses'][TEST_ACC4]}
            assert NFT_ID_FOR_TEST_ACC4 not in all_nfts_ids
        else:
            assert result == {
                'entries': [],
                'entries_found': 0,
                'entries_total': 0,
                'total_value': '0',
            }

    # remove the nft from the ignored list.
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredassetsresource',
        ),
        json={'assets': [NFT_ID_FOR_TEST_ACC4]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['successful'] == [NFT_ID_FOR_TEST_ACC4]

    # query the nfts endpoint again and verify that the nft is present
    with get_all_nft_data_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                endpoint,
            ),
            json={'async_query': False, 'ignore_cache': True},
        )
        result = assert_proper_sync_response_with_result(response)
        if endpoint == 'nftsresource':
            all_nfts_ids = {nft['token_identifier'] for nft in result['addresses'][TEST_ACC4]}
        else:
            all_nfts_ids = {nft['id'] for nft in result['entries']}
        assert NFT_ID_FOR_TEST_ACC4 in all_nfts_ids


@requires_env([TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
@pytest.mark.parametrize('ethereum_accounts', [['0x7277F7849966426d345D8F6B9AFD1d3d89183083']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_no_price(rotkehlchen_api_server: 'APIServer') -> None:
    """Test for nft with no price and that query works fine"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    nft_module = rotki.chains_aggregator.get_module('nfts')
    assert nft_module is not None

    def mock_session_get(url: str, params: Any, timeout: int) -> MockResponse:  # pylint: disable=unused-argument
        if '/nfts' in url:
            response = """
            {
                "nfts": [
                    {
                    "identifier": "336510496872176433120578",
                    "collection": "devcon-vi-souvenir-v4",
                    "contract": "0x7522dc5a357891b4daec194e285551ea5ea66d09",
                    "token_standard": "erc721",
                    "name": "Devcon VI Souvenir",
                    "description": "Devcon is the Ethereum conference for developers, researchers, thinkers, and makers.An intensive introduction for new Ethereum explorers, a global family reunion for those already a part of our ecosystem, and a source of energy and creativity for all. This ticket NFT serves as a souvenir for Devcon Bogota. With a symbolic focus on LATAM, and the beautiful destination of Bogota Colombia. The bird of paradise is known as the ultimate symbol of paradise and freedom. Due to its tropical nature, this flower symbolizes freedom and joy.",
                    "image_url": "https://resources.smarttokenlabs.com/devcon6/ETH.webp",
                    "metadata_url": "https://resources.smarttokenlabs.com/1/0x7522dc5a357891b4daec194e285551ea5ea66d09/336510496872176433120578",
                    "opensea_url": "https://opensea.io/assets/ethereum/0x7522dc5a357891b4daec194e285551ea5ea66d09/336510496872176433120578",
                    "updated_at": "2022-10-17T06:36:48.750908",
                    "is_disabled": false,
                    "is_nsfw": false
                    }
                ]
            }"""  # noqa: E501
        elif '/stats' in url:
            response = """{
                "total": {
                    "volume": 0,
                    "sales": 0,
                    "average_price": 0,
                    "num_owners": 435,
                    "market_cap": 0,
                    "floor_price": 0,
                    "floor_price_symbol": ""
                }
            }"""
        elif '/collections/' in url:
            response = """{
                "contracts": [{"address":1,"chain":"ethereum"}, {"address":2,"chain":"ethereum"}],
                "name": "Devcon VI Souvenir V4",
                "collection": "devcon-vi-souvenir-v4",
                "banner_image_url": "url",
                "image_url": "url",
                "description": "bla bla"
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
    result = assert_proper_sync_response_with_result(response)
    assert result == {
        'entries': [
            {
                'id': '_nft_0x7522dC5A357891B4dAEC194E285551EA5ea66d09_336510496872176433120578',
                'name': 'Devcon VI Souvenir',
                'price_in_asset': '0',
                'price_asset': 'ETH',
                'manually_input': False,
                'is_lp': False,
                'image_url': 'https://resources.smarttokenlabs.com/devcon6/ETH.webp',
                'price': '0.0',
                'collection_name': 'Devcon VI Souvenir V4',
            },
        ],
        'entries_found': 1,
        'entries_total': 1,
        'total_value': '0.0',
    }


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4, TEST_ACC5]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_customized_queried_addresses(rotkehlchen_api_server: 'APIServer') -> None:
    """
    Test that if queried addresses are customized for nfts module, then from /nfts/balances only
    NFTs of those addresses are returned"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def mock_get_all_nft_data(
            _addresses: list[ChecksumEvmAddress],
            **_kwargs,
        ) -> tuple[dict[ChecksumEvmAddress, Any], int]:
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
        result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 1 and result['entries'][0]['name'] == TEST_NFT_NEBOLAX_ETH.name  # noqa: E501
