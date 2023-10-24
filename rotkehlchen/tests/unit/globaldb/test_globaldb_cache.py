import datetime
import json
from contextlib import suppress
from unittest.mock import patch

import pytest
import requests
from freezegun import freeze_time

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.ethereum.modules.convex.convex_cache import (
    query_convex_data,
    read_convex_data_from_cache,
    save_convex_data_to_cache,
)
from rotkehlchen.chain.ethereum.modules.curve.curve_cache import CURVE_API_URLS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.velodrome.velodrome_cache import (
    query_velodrome_data,
    read_velodrome_pools_and_gauges_from_cache,
    save_velodrome_data_to_cache,
)
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.filtering import AddressbookFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_values,
    globaldb_get_unique_cache_value,
    read_curve_pool_tokens,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    AddressbookEntry,
    CacheType,
    ChainID,
    EvmTokenKind,
    SupportedBlockchain,
)

CURVE_EXPECTED_LP_TOKENS_TO_POOLS = {
    # first 2 are registry pools
    '0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490': '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7',
    '0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900': '0xDeBF20617708857ebe4F679508E7b7863a8A8EeE',
}

CURVE_EXPECTED_POOL_COINS = {
    # first 2 are registry pools
    '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7': [
        '0x6B175474E89094C44Da98b954EedeAC495271d0F',
        '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    ],
    '0xDeBF20617708857ebe4F679508E7b7863a8A8EeE': [
        '0x028171bCA77440897B824Ca71D1c56caC55b68A3',
        '0xBcca60bB61934080951369a648Fb03DF4F96263C',
        '0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811',
    ],
}

CURVE_EXPECTED_GAUGES = {
    '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7': '0xbFcF63294aD7105dEa65aA58F8AE5BE2D9d0952A',
    '0xDeBF20617708857ebe4F679508E7b7863a8A8EeE': '0xd662908ADA2Ea1916B3318327A97eB18aD588b5d',
}

CURVE_EXPECTED_ADDRESBOOK_ENTRIES_FROM_API = [
    AddressbookEntry(
        address=string_to_evm_address('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7'),
        name='Curve.fi DAI/USDC/USDT',
        blockchain=SupportedBlockchain.ETHEREUM,
    ), AddressbookEntry(
        address=string_to_evm_address('0xbFcF63294aD7105dEa65aA58F8AE5BE2D9d0952A'),
        name='Curve gauge for Curve.fi DAI/USDC/USDT',
        blockchain=SupportedBlockchain.ETHEREUM,
    ), AddressbookEntry(
        address=string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE'),
        name='Curve.fi aDAI/aUSDC/aUSDT',
        blockchain=SupportedBlockchain.ETHEREUM,
    ), AddressbookEntry(
        address=string_to_evm_address('0xd662908ADA2Ea1916B3318327A97eB18aD588b5d'),
        name='Curve gauge for Curve.fi aDAI/aUSDC/aUSDT',
        blockchain=SupportedBlockchain.ETHEREUM,
    ),
]

CURVE_EXPECTED_ADDRESBOOK_ENTRIES_FROM_CHAIN = [
    AddressbookEntry(
        address=string_to_evm_address('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7'),
        name='3pool',
        blockchain=SupportedBlockchain.ETHEREUM,
    ), AddressbookEntry(
        address=string_to_evm_address('0xbFcF63294aD7105dEa65aA58F8AE5BE2D9d0952A'),
        name='Curve gauge for 3pool',
        blockchain=SupportedBlockchain.ETHEREUM,
    ), AddressbookEntry(
        address=string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE'),
        name='aave',
        blockchain=SupportedBlockchain.ETHEREUM,
    ), AddressbookEntry(
        address=string_to_evm_address('0xd662908ADA2Ea1916B3318327A97eB18aD588b5d'),
        name='Curve gauge for aave',
        blockchain=SupportedBlockchain.ETHEREUM,
    ),
]

VELODROME_SOME_EXPECTED_POOLS = {
    string_to_evm_address('0x904f14F9ED81d0b0a40D8169B28592aac5687158'),
    string_to_evm_address('0x7A7f1187c4710010DB17d0a9ad3fcE85e6ecD90a'),
    string_to_evm_address('0x8134A2fDC127549480865fB8E5A9E8A8a95a54c5'),
    string_to_evm_address('0x6e6046E9b5E3D90eac2ABbA610bcA725834Ca5b3'),
    string_to_evm_address('0x58e6433A6903886E440Ddf519eCC573c4046a6b2'),
}

VELODROME_SOME_EXPECTED_GAUGES = {
    string_to_evm_address('0x91f2e5c009D3742188FA77619582402681d73f98'),
    string_to_evm_address('0xeC9df85F362D3EBc4b9CA0eD7d7fDecF8Cfbdeb8'),
    string_to_evm_address('0x84195De69B8B131ddAa4Be4F75633fCD7F430b7c'),
    string_to_evm_address('0xbcD875fADEd3D2b9458EA6b86Bd5283075D78a06'),
    string_to_evm_address('0x8329c9c93B63dB8a56a3b9a0c44c2edAbD6572A8'),
}

VELODROME_SOME_EXPECTED_ASSETS = [
    'eip155:10/erc20:0x8134A2fDC127549480865fB8E5A9E8A8a95a54c5',
    'eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
    'eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607',
]

VELODROME_SOME_EXPECTED_ADDRESBOOK_ENTRIES = [
    AddressbookEntry(
        address=string_to_evm_address('0x904f14F9ED81d0b0a40D8169B28592aac5687158'),
        name='Velodrome pool sAMMV2-opxveVELO/VELO',
        blockchain=SupportedBlockchain.OPTIMISM,
    ), AddressbookEntry(
        address=string_to_evm_address('0x7A7f1187c4710010DB17d0a9ad3fcE85e6ecD90a'),
        name='Velodrome pool vAMMV2-RED/VELO',
        blockchain=SupportedBlockchain.OPTIMISM,
    ), AddressbookEntry(
        address=string_to_evm_address('0x8134A2fDC127549480865fB8E5A9E8A8a95a54c5'),
        name='Velodrome pool vAMMV2-USDC/VELO',
        blockchain=SupportedBlockchain.OPTIMISM,
    ), AddressbookEntry(
        address=string_to_evm_address('0x6e6046E9b5E3D90eac2ABbA610bcA725834Ca5b3'),
        name='Velodrome pool vAMMV2-UNLOCK/VELO',
        blockchain=SupportedBlockchain.OPTIMISM,
    ), AddressbookEntry(
        address=string_to_evm_address('0x58e6433A6903886E440Ddf519eCC573c4046a6b2'),
        name='Velodrome pool vAMMV2-WETH/VELO',
        blockchain=SupportedBlockchain.OPTIMISM,
    ),
]


def get_velodrome_addressbook_and_asset_identifiers(optimism_inquirer):
    with GlobalDBHandler().conn.read_ctx() as cursor:
        addressbook_entries = DBAddressbook(optimism_inquirer.database).get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(),
        )[0]
        asset_identifiers = cursor.execute('SELECT identifier FROM assets').fetchall()
    return addressbook_entries, asset_identifiers


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_velodrome_cache(optimism_inquirer):
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # make sure that velodrome cache is clear of expected pools and gauges
        for pool in VELODROME_SOME_EXPECTED_POOLS | VELODROME_SOME_EXPECTED_GAUGES:
            write_cursor.execute(f'DELETE FROM general_cache WHERE value LIKE "%{pool}%"')
            write_cursor.execute(f'DELETE FROM address_book WHERE address="{pool}"')

        for asset in VELODROME_SOME_EXPECTED_ASSETS:
            write_cursor.execute(f'DELETE FROM assets WHERE identifier LIKE "%{asset}%"')

    pools, gauges = read_velodrome_pools_and_gauges_from_cache()
    assert not pools & VELODROME_SOME_EXPECTED_POOLS
    assert not gauges & VELODROME_SOME_EXPECTED_GAUGES
    addressbook_entries, asset_identifiers = get_velodrome_addressbook_and_asset_identifiers(optimism_inquirer)  # noqa: E501
    assert not any(entry in addressbook_entries for entry in VELODROME_SOME_EXPECTED_ADDRESBOOK_ENTRIES)  # noqa: E501
    assert not any((identifier,) in asset_identifiers for identifier in VELODROME_SOME_EXPECTED_ASSETS)  # noqa: E501

    optimism_inquirer.ensure_cache_data_is_updated(
        cache_type=CacheType.VELODROME_POOL_ADDRESS,
        query_method=query_velodrome_data,
        save_method=save_velodrome_data_to_cache,
    )  # populates cache, addressbook and assets tables
    pools, gauges = read_velodrome_pools_and_gauges_from_cache()
    assert pools >= VELODROME_SOME_EXPECTED_POOLS
    assert gauges >= VELODROME_SOME_EXPECTED_GAUGES
    addressbook_entries, asset_identifiers = get_velodrome_addressbook_and_asset_identifiers(optimism_inquirer)  # noqa: E501
    assert all(entry in addressbook_entries for entry in VELODROME_SOME_EXPECTED_ADDRESBOOK_ENTRIES)  # noqa: E501
    assert all((identifier,) in asset_identifiers for identifier in VELODROME_SOME_EXPECTED_ASSETS)


@pytest.mark.vcr()
def test_convex_cache(ethereum_inquirer):
    """Test convex pools querying and caching mechanism"""
    convex_expected_pools = {  # some expected pools
        string_to_evm_address('0x49Dd6BCf56ABBE00DbB816EF6664c4cf5bdd81A1'): 'dYFIETH-f',
        string_to_evm_address('0xDe91Bf29ADF79FbfbbF0d646EAf024c0CB9fac25'): 'crvstUSDT-f',
        string_to_evm_address('0x62f3C96017F2Ba9D83BD70500B738FEEebc5FFc6'): 'crvSTBT-f',
        string_to_evm_address('0xFe4aC9cd3892BACbeA12C9185a577164f56831fD'): 'ETHxfrxETH-f',
    }.items()
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # make sure that convex cache is clear of expected pools
        for pool, _ in convex_expected_pools:
            write_cursor.execute(f'DELETE FROM general_cache WHERE value="{pool}"')
            write_cursor.execute(f'DELETE FROM unique_cache WHERE key LIKE "%{pool}%"')

    assert not read_convex_data_from_cache()[0].items() & convex_expected_pools

    ethereum_inquirer.ensure_cache_data_is_updated(
        cache_type=CacheType.CONVEX_POOL_ADDRESS,
        query_method=query_convex_data,
        save_method=save_convex_data_to_cache,
        force_refresh=True,
    )  # populates convex caches
    assert len(read_convex_data_from_cache()[0].items() & convex_expected_pools) == 4


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('use_curve_api', [True, False])
def test_curve_cache(rotkehlchen_instance, use_curve_api):
    """Test curve pools fetching mechanism"""
    # Set initial cache data to check that it is gone after the cache update
    ethereum_inquirer = rotkehlchen_instance.chains_aggregator.ethereum.node_inquirer
    db_addressbook = DBAddressbook(ethereum_inquirer.database)
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # make sure that curve cache is clear at the beginning
        write_cursor.execute('DELETE FROM general_cache WHERE key LIKE "%CURVE%"')

    # delete one of the tokens to check that it is created during the update
    with suppress(InputError):
        GlobalDBHandler().delete_evm_token(  # token may not exist but we don't care
            address='0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811',  # aUSDT
            chain_id=ChainID.ETHEREUM,
        )
    AssetResolver().clean_memory_cache(identifier=evm_address_to_identifier(
        address='0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811',
        chain_id=ChainID.ETHEREUM,
        token_type=EvmTokenKind.ERC20,
    ))

    # check that it was deleted successfully
    token = GlobalDBHandler().get_evm_token(
        address='0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811',
        chain_id=ChainID.ETHEREUM,
    )
    assert token is None

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute('DELETE FROM address_book')
    with GlobalDBHandler().conn.read_ctx() as cursor:
        known_addresses = db_addressbook.get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(),
        )[0]
    assert len(known_addresses) == 0

    curve_address_provider = ethereum_inquirer.contracts.contract(string_to_evm_address('0x0000000022D53366457F9d5E68Ec105046FC4383'))  # noqa: E501

    def mock_call_contract(contract, node_inquirer, method_name, **kwargs):
        if use_curve_api is True:
            assert contract != curve_address_provider, 'There should be no calls to curve on-chain contracts if api is used'  # noqa: E501
        if method_name == 'pool_count':
            return 2  # if we don't limit pools count, the test will run for too long
        return node_inquirer.call_contract(
            contract_address=contract.address,
            abi=contract.abi,
            method_name=method_name,
            **kwargs,
        )

    call_contract_patch = patch(
        target='rotkehlchen.chain.evm.contracts.EvmContract.call',
        new=mock_call_contract,
    )

    requests_get = requests.get

    def mock_requests_get(url, timeout):  # pylint: disable=unused-argument
        """Mock requests.get.
        requests.get in this test should be used only for curve api queries.
        If use_curve_api is False, return success: False so that curve cache query fallbacks to
        chain query.
        If use_curve_api is True, then to minimize number of pools check in this test, return
        empty pools list for 3 out of the 4 curve api endpoints and for the remaining one perform
        a real request and take from the response only 2 first pools.
        """
        if url not in CURVE_API_URLS:
            raise AssertionError(f'Unexpected url {url} was called')

        if use_curve_api is False:
            return MockResponse(status_code=200, text=json.dumps({'success': False, 'data': {'poolData': []}}))  # noqa: E501

        if url != CURVE_API_URLS[0]:
            return MockResponse(status_code=200, text=json.dumps({'success': True, 'data': {'poolData': []}}))  # noqa: E501

        response_json = requests_get(url).json()
        response_json['data']['poolData'] = response_json['data']['poolData'][:2]
        return MockResponse(status_code=200, text=json.dumps(response_json))

    requests_patch = patch(
        'requests.get',
        side_effect=mock_requests_get,
    )

    future_timestamp = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), call_contract_patch, requests_patch:
        rotkehlchen_instance.chains_aggregator.ethereum.assure_curve_cache_is_queried_and_decoder_updated()

    lp_tokens_to_pools_in_cache = {}
    pool_coins_in_cache = {}
    gauges_in_cache = {}
    with GlobalDBHandler().conn.read_ctx() as cursor:
        lp_tokens_in_cache = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(CacheType.CURVE_LP_TOKENS,),
        )
        for lp_token_addr in lp_tokens_in_cache:
            pool_addr = globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.CURVE_POOL_ADDRESS, lp_token_addr),
            )
            lp_tokens_to_pools_in_cache[lp_token_addr] = pool_addr

            pool_coins_in_cache[pool_addr] = read_curve_pool_tokens(cursor=cursor, pool_address=pool_addr)  # noqa: E501

            gauge_data = globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.CURVE_GAUGE_ADDRESS, pool_addr),
            )
            if gauge_data is None:
                gauges_in_cache[pool_addr] = None
            else:
                gauges_in_cache[pool_addr] = gauge_data

    assert lp_tokens_to_pools_in_cache == CURVE_EXPECTED_LP_TOKENS_TO_POOLS
    assert pool_coins_in_cache == CURVE_EXPECTED_POOL_COINS
    assert gauges_in_cache == CURVE_EXPECTED_GAUGES

    # Check that the token was created
    token = GlobalDBHandler().get_evm_token(
        address='0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811',
        chain_id=ChainID.ETHEREUM,
    )
    assert token.name == 'Aave interest bearing USDT'
    assert token.symbol == 'aUSDT'
    assert token.decimals == 6

    # Check that initially set values are gone
    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert 'key123' not in globaldb_get_general_cache_values(cursor, key_parts=(CacheType.CURVE_LP_TOKENS,))  # noqa: E501
        assert globaldb_get_unique_cache_value(cursor, key_parts=(CacheType.CURVE_POOL_ADDRESS, 'abc')) is None  # noqa: E501
        assert globaldb_get_unique_cache_value(cursor, key_parts=(CacheType.CURVE_POOL_TOKENS, 'pool-address-1')) is None  # noqa: E501
        assert globaldb_get_unique_cache_value(cursor, key_parts=(CacheType.CURVE_GAUGE_ADDRESS, 'pool-address-1')) is None  # noqa: E501

    with GlobalDBHandler().conn.read_ctx() as cursor:
        known_addresses = db_addressbook.get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(),
        )[0]
    if use_curve_api:
        assert known_addresses == CURVE_EXPECTED_ADDRESBOOK_ENTRIES_FROM_API
    else:
        assert known_addresses == CURVE_EXPECTED_ADDRESBOOK_ENTRIES_FROM_CHAIN
