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
from rotkehlchen.tests.conftest import TestEnvironment, requires_env
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
TEST_ACC5 = '0x4bBa290826C253BD854121346c370a9886d1bC26'  # nebolax.eth
TEST_ACC6 = '0x3e649c5Eac6BBEE8a4F2A2945b50d8e582faB3bf'  # contains a uniswap-v3 nft
NFT_ID_FOR_TEST_ACC4 = '_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041'  # noqa: E501
NFT_ID_FOR_TEST_ACC5 = '_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_73552724610198397480670284492690114609730214421511097849210414928326607694469'  # noqa: E501
NFT_ID_FOR_TEST_ACC6_1 = '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_360680'
NFT_ID_FOR_TEST_ACC6_2 = '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_360762'


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


@requires_env([TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
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


@requires_env([TestEnvironment.NIGHTLY, TestEnvironment.NFTS])
# @flaky(max_runs=3, min_passes=1)  # all opensea calls have become quite flaky
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
    assert result['entries'] == {}, 'nothing should be returned with ignore_cache=False until nfts are queried'  # noqa: E501

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': True})
    result_ignored_cache = assert_proper_response_with_result(response)
    assert result_ignored_cache['entries_found'] == 4
    for nfts_balances in result_ignored_cache['entries'].values():
        for nft_balance in nfts_balances:
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
    assert result['entries'][TEST_ACC5][0]['id'] == NFT_ID_FOR_TEST_ACC5

    # ignore an nft
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredassetsresource',
        ),
        json={'assets': [NFT_ID_FOR_TEST_ACC4, NFT_ID_FOR_TEST_ACC6_2]},
    )

    # Check that filtering ignored nfts works
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'ignored_assets_handling': 'none'})
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 4
    assert result['entries'][TEST_ACC4][0]['id'] == NFT_ID_FOR_TEST_ACC4
    assert result['entries'][TEST_ACC5][0]['id'] == NFT_ID_FOR_TEST_ACC5
    assert result['entries'][TEST_ACC6][0]['id'] == NFT_ID_FOR_TEST_ACC6_1
    assert result['entries'][TEST_ACC6][1]['id'] == NFT_ID_FOR_TEST_ACC6_2
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'ignored_assets_handling': 'exclude'})
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 2
    expected_nfts_without_ignored = {NFT_ID_FOR_TEST_ACC5, NFT_ID_FOR_TEST_ACC6_1}
    assert {entry[0]['id'] for entry in result['entries'].values()} == expected_nfts_without_ignored  # noqa: E501
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'nftsbalanceresource',
    ), json={'async_query': False, 'ignore_cache': False, 'ignored_assets_handling': 'show only'})
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 2
    assert result['entries'][TEST_ACC4][0]['id'] == NFT_ID_FOR_TEST_ACC4
    assert result['entries'][TEST_ACC6][0]['id'] == NFT_ID_FOR_TEST_ACC6_2

    response = requests.get(api_url_for(
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


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC4, TEST_ACC5]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_edit_delete_nft(rotkehlchen_api_server):
    """Check that ignoring NFTs work as expected"""
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    nft_map = {
        TEST_ACC4: [
            NFT(
                token_identifier='_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041',  # noqa: E501
                background_color=None,
                image_url='https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg',  # noqa: E501
                name='yabir.eth',
                external_link='https://app.ens.domains/name/yabir.eth',
                permalink='https://opensea.io/assets/ethereum/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/26612040215479394739615825115912800930061094786769410446114278812336794170041',  # noqa: E501
                price_eth=FVal(0.0006899),
                price_usd=FVal(1.32),
                collection=Collection(
                    name='ENS: Ethereum Name Service',
                    banner_image='',
                    description='Ethereum Name Service (ENS) domains are secure domain names for the decentralized world. ENS domains provide a way for users to map human readable names to blockchain and non-blockchain resources, like Ethereum addresses, IPFS hashes, or website URLs. ENS domains can be bought and sold on secondary markets.',  # noqa: E501
                    large_image='https://i.seadn.io/gae/BBj09xD7R4bBtg1lgnAAS9_TfoYXKwMtudlk-0fVljlURaK7BWcARCpkM-1LGNGTAcsGO6V1TgrtmQFvCo8uVYW_QEfASK-9j6Nr?w=500&auto=format',  # noqa: E501
                    floor_price=FVal(0.0006899),
                ),
            ),
        ],
        TEST_ACC5: [
            NFT(
                token_identifier='_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_73552724610198397480670284492690114609730214421511097849210414928326607694469',  # noqa: E501
                background_color=None,
                image_url='https://openseauserdata.com/files/8fd18b22e4c81aff3998956e7a712d93.svg',
                name='nebolax.eth',
                external_link='https://app.ens.domains/name/nebolax.eth',
                permalink='https://opensea.io/assets/ethereum/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/73552724610198397480670284492690114609730214421511097849210414928326607694469',  # noqa: E501
                price_eth=FVal(0.0012),
                price_usd=FVal(2.65),
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

    def mock_get_all_nft_data(addresses, **kwargs):  # pylint: disable=unused-argument
        return nft_map, sum([len(x) for x in nft_map.values()])

    get_all_nft_data_patch = patch(
        'rotkehlchen.chain.ethereum.modules.nfts.Nfts._get_all_nft_data',
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
        assert result['entries'][TEST_ACC5][0]['price_in_asset'] == '0.0012'
        assert result['entries'][TEST_ACC5][0]['image_url'] == 'https://openseauserdata.com/files/8fd18b22e4c81aff3998956e7a712d93.svg'  # noqa: E501

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
            price_usd=FVal(553.7),
            collection=Collection(
                name='ENS: Ethereum Name Service',
                banner_image='',
                description='Ethereum Name Service (ENS) domains are secure domain names for the decentralized world. ENS domains provide a way for users to map human readable names to blockchain and non-blockchain resources, like Ethereum addresses, IPFS hashes, or website URLs. ENS domains can be bought and sold on secondary markets.',  # noqa: E501
                large_image='https://i.seadn.io/gae/BBj09xD7R4bBtg1lgnAAS9_TfoYXKwMtudlk-0fVljlURaK7BWcARCpkM-1LGNGTAcsGO6V1TgrtmQFvCo8uVYW_QEfASK-9j6Nr?w=500&auto=format',  # noqa: E501
                floor_price=FVal(0.0006899),
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
        assert result['entries'][TEST_ACC5][0]['price_in_asset'] == '0.5'
        assert result['entries'][TEST_ACC5][0]['image_url'] == 'https://openseauserdata.com/files/3f7c0c7d1ba51e61fe05ef53875f9f7e.svg'  # noqa: E501

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
        assert result['entries_found'] == 1
        assert TEST_ACC4 in result['entries']

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
            assert result == {'entries': {}, 'entries_found': 0, 'entries_total': 0}

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
            all_nfts_ids = {nft['id'] for nft in result['entries'][TEST_ACC4]}
        assert NFT_ID_FOR_TEST_ACC4 in all_nfts_ids
