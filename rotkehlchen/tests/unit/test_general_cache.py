import datetime
import json
from contextlib import suppress
from unittest.mock import patch

import pytest
import requests
from freezegun import freeze_time

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.ethereum.modules.curve.curve_cache import CURVE_API_URLS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_values, read_curve_pool_tokens
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    AddressbookEntry,
    ChainID,
    EvmTokenKind,
    GeneralCacheType,
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

EXPECTED_ADDRESBOOK_ENTRIES_FROM_API = [
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

EXPECTED_ADDRESBOOK_ENTRIES_FROM_CHAIN = [
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


@pytest.mark.vcr()
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
        known_addresses = db_addressbook.get_addressbook_entries(cursor=cursor)
    assert len(known_addresses) == 0

    curve_address_provider = ethereum_inquirer.contracts.contract('CURVE_ADDRESS_PROVIDER')  # noqa: E501

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
        rotkehlchen_instance.chains_aggregator.ethereum.assure_curve_cache_is_queried_and_decoder_updated()  # noqa: E501

    lp_tokens_to_pools_in_cache = {}
    pool_coins_in_cache = {}
    gauges_in_cache = {}
    with GlobalDBHandler().conn.read_ctx() as cursor:
        lp_tokens_in_cache = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
        )
        for lp_token_addr in lp_tokens_in_cache:
            pool_addr = globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token_addr],
            )[0]
            lp_tokens_to_pools_in_cache[lp_token_addr] = pool_addr

            pool_coins_in_cache[pool_addr] = read_curve_pool_tokens(cursor=cursor, pool_address=pool_addr)  # noqa: E501

            gauge_data = globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=[GeneralCacheType.CURVE_GAUGE_ADDRESS, pool_addr],
            )
            if len(gauge_data) == 0:
                gauges_in_cache[pool_addr] = None
            else:
                assert len(gauge_data) == 1, 'Should always be at max 1 gauge per pool'
                gauges_in_cache[pool_addr] = gauge_data[0]

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
        assert 'key123' not in globaldb_get_general_cache_values(cursor, key_parts=[GeneralCacheType.CURVE_LP_TOKENS])  # noqa: E501
        assert len(globaldb_get_general_cache_values(cursor, key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, 'abc'])) == 0  # noqa: E501
        assert len(globaldb_get_general_cache_values(cursor, key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, 'pool-address-1'])) == 0  # noqa: E501
        assert len(globaldb_get_general_cache_values(cursor, key_parts=[GeneralCacheType.CURVE_GAUGE_ADDRESS, 'pool-address-1'])) == 0  # noqa: E501

    with GlobalDBHandler().conn.read_ctx() as cursor:
        known_addresses = db_addressbook.get_addressbook_entries(cursor=cursor)
    if use_curve_api:
        assert known_addresses == EXPECTED_ADDRESBOOK_ENTRIES_FROM_API
    else:
        assert known_addresses == EXPECTED_ADDRESBOOK_ENTRIES_FROM_CHAIN
