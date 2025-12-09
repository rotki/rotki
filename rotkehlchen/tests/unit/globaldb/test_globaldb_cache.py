import datetime
import json
import logging
from collections.abc import Callable
from contextlib import suppress
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, _Call, call, patch

import pytest
import requests
from freezegun import freeze_time

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.utils import get_evm_token
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.ethereum.modules.convex.convex_cache import (
    query_convex_data,
    read_convex_data_from_cache,
)
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.decoding.balancer.balancer_cache import (
    query_balancer_data,
    read_balancer_pools_and_gauges_from_cache,
)
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V2
from rotkehlchen.chain.evm.decoding.beefy_finance.constants import CPT_BEEFY_FINANCE
from rotkehlchen.chain.evm.decoding.beefy_finance.utils import query_beefy_vaults
from rotkehlchen.chain.evm.decoding.curve.constants import (
    CPT_CURVE,
    CURVE_ADDRESS_PROVIDER,
    CURVE_API_URL,
    CURVE_CHAIN_ID,
)
from rotkehlchen.chain.evm.decoding.curve.curve_cache import read_curve_pools_and_gauges
from rotkehlchen.chain.evm.decoding.gearbox.constants import (
    CHAIN_ID_TO_DATA_COMPRESSOR,
    CPT_GEARBOX,
)
from rotkehlchen.chain.evm.decoding.gearbox.gearbox_cache import (
    GearboxPoolData,
    get_gearbox_pool_tokens,
    query_gearbox_data,
    read_gearbox_data_from_cache,
)
from rotkehlchen.chain.evm.decoding.superfluid.constants import CPT_SUPERFLUID
from rotkehlchen.chain.evm.decoding.superfluid.utils import query_superfluid_tokens
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    POOL_DATA_CHUNK_SIZE,
    query_velodrome_like_data,
    read_velodrome_pools_and_gauges_from_cache,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.velodrome.constants import A_VELO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.filtering import AddressbookFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    AddressbookEntry,
    CacheType,
    ChainID,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.interfaces import ReloadableDecoderMixin
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

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
    '0xbFcF63294aD7105dEa65aA58F8AE5BE2D9d0952A',
    '0xd662908ADA2Ea1916B3318327A97eB18aD588b5d',
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
    'eip155:10/erc20:0x7A7f1187c4710010DB17d0a9ad3fcE85e6ecD90a',  # RED/VELO pool token
    'eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607',  # USDC
    A_VELO.identifier,
]

GEARBOX_SOME_EXPECTED_POOLS = {
    string_to_evm_address('0xda00000035fef4082F78dEF6A8903bee419FbF8E'),
    string_to_evm_address('0xda00010eDA646913F273E10E7A5d1F659242757d'),
    string_to_evm_address('0xda0002859B2d05F66a753d8241fCDE8623f26F4f'),
    string_to_evm_address('0x1DC0F3359a254f876B37906cFC1000A35Ce2d717'),
    string_to_evm_address('0x31426271449F60d37Cc5C9AEf7bD12aF3BdC7A94'),
}

GEARBOX_SOME_EXPECTED_ASSETS = [
    'eip155:1/erc20:0xda00000035fef4082F78dEF6A8903bee419FbF8E',
    'eip155:1/erc20:0xc411dB5f5Eb3f7d552F9B8454B2D74097ccdE6E3',
    'eip155:1/erc20:0xe753260F1955e8678DCeA8887759e07aa57E8c54',
    'eip155:1/erc20:0xda00010eDA646913F273E10E7A5d1F659242757d',
    'eip155:1/erc20:0x31426271449F60d37Cc5C9AEf7bD12aF3BdC7A94',
    'eip155:1/erc20:0x865377367054516e17014CcdED1e7d814EDC9ce4',
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

BALANCER_SOME_EXPECTED_POOLS = {string_to_evm_address('0xf01b0684C98CD7aDA480BFDF6e43876422fa1Fc1')}  # noqa: E501

BALANCER_SOME_EXPECTED_GAUGES = {string_to_evm_address('0xdf54d2Dd06F8Be3B0c4FfC157bE54EC9cca91F3C')}  # noqa: E501


def get_velodrome_addressbook_and_asset_identifiers(optimism_inquirer):
    with GlobalDBHandler().conn.read_ctx() as cursor:
        addressbook_entries = DBAddressbook(optimism_inquirer.database).get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(),
        )[0]
        asset_identifiers = cursor.execute('SELECT identifier FROM assets').fetchall()
    return addressbook_entries, asset_identifiers


def address_in_addressbook(address, cursor):
    return cursor.execute('SELECT address FROM address_book WHERE address=?', (address,)).fetchone() is not None  # noqa: E501


def make_call_object(protocol: str, chain: ChainID, processed: int, total: int) -> _Call:
    """Create a call object for the given protocol, chain, processed and total."""
    return call(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'protocol': protocol,
            'chain': chain,
            'subtype': str(ProgressUpdateSubType.PROTOCOL_CACHE_UPDATES),
            'processed': processed,
            'total': total,
        },
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_velodrome_cache(optimism_inquirer):
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # make sure that velodrome cache is clear of expected pools and gauges
        for pool in VELODROME_SOME_EXPECTED_POOLS | VELODROME_SOME_EXPECTED_GAUGES:
            write_cursor.execute(f"DELETE FROM general_cache WHERE value LIKE '%{pool}%'")
            write_cursor.execute('DELETE FROM address_book WHERE address=?', (pool,))

        for asset in VELODROME_SOME_EXPECTED_ASSETS:
            write_cursor.execute('DELETE FROM assets WHERE identifier=?', (asset,))

    pools, gauges = read_velodrome_pools_and_gauges_from_cache()
    assert not pools & VELODROME_SOME_EXPECTED_POOLS
    assert not gauges & VELODROME_SOME_EXPECTED_GAUGES
    addressbook_entries, asset_identifiers = get_velodrome_addressbook_and_asset_identifiers(optimism_inquirer)  # noqa: E501
    assert not any(entry in addressbook_entries for entry in VELODROME_SOME_EXPECTED_ADDRESBOOK_ENTRIES)  # noqa: E501
    assert not any((identifier,) in asset_identifiers for identifier in VELODROME_SOME_EXPECTED_ASSETS)  # noqa: E501
    call_count = 0

    def make_mock_call_contract(force_refresh: bool) -> Callable:
        def mock_call_contract(contract, node_inquirer, method_name, **kwargs):
            """Limit pool query to only the first five pools"""
            nonlocal call_count
            if method_name == 'all':
                if force_refresh is True:
                    assert kwargs['arguments'] == [POOL_DATA_CHUNK_SIZE, 0]  # starts from the beginning  # noqa: E501
                    return []  # don't return any pools. Will test the rest of the pool processing when force_refresh is False  # noqa: E501

                if call_count > 0:
                    return []  # only do a single chunk

                assert kwargs['arguments'] == [POOL_DATA_CHUNK_SIZE, 1402]  # only tries to query new pools  # noqa: E501
                kwargs['arguments'] = [5, 0]  # Only query the first 5 pools for simpler testing
                call_count += 1

            return node_inquirer.call_contract(
                contract_address=contract.address,
                abi=contract.abi,
                method_name=method_name,
                **kwargs,
            )

        return mock_call_contract

    for force_refresh in (True, False):
        with (
            patch(target='rotkehlchen.chain.evm.contracts.EvmContract.call', new=make_mock_call_contract(force_refresh)),  # noqa: E501
            patch.object(optimism_inquirer.database.msg_aggregator, 'add_message'),
            patch('rotkehlchen.chain.evm.node_inquirer.should_update_protocol_cache', return_value=True),  # noqa: E501
        ):
            optimism_inquirer.ensure_cache_data_is_updated(
                cache_type=CacheType.VELODROME_POOL_ADDRESS,
                query_method=query_velodrome_like_data,
                force_refresh=force_refresh,
            )  # populates cache, addressbook and assets tables

    pools, gauges = read_velodrome_pools_and_gauges_from_cache()
    assert pools >= VELODROME_SOME_EXPECTED_POOLS
    assert gauges >= VELODROME_SOME_EXPECTED_GAUGES
    addressbook_entries, asset_identifiers = get_velodrome_addressbook_and_asset_identifiers(optimism_inquirer)  # noqa: E501
    assert all(entry in addressbook_entries for entry in VELODROME_SOME_EXPECTED_ADDRESBOOK_ENTRIES)  # noqa: E501
    assert all((identifier,) in asset_identifiers for identifier in VELODROME_SOME_EXPECTED_ASSETS)


class MockEvmContract:
    """A mock contract class that returns a desired result for a `call` function.
    Used for `test_velodrome_cache_with_no_symbol`."""
    def call(self, **kwargs):
        if kwargs['method_name'] == 'all':
            return [{
                0: '0x3241738149B24C9164dA14Fa2040159FFC6Dd237',
                1: '',
                2: 18,
                4: 10,
                7: '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85',
                10: '0xdFA46478F9e5EA86d57387849598dbFB2e964b02',
                13: '0xBe3235e341393e43949aAd6F073982F67BFF412f',
                16: '0x25dEc77FC1c2b67582DD2237dA427d3E3Be94259',
                17: '0x0000000000000000000000000000000000000000',
            }]
        else:
            return []


def test_velodrome_cache_with_no_symbol(optimism_inquirer: 'OptimismInquirer'):
    """Test a case when a queried pool is not a valid ERC20 token,
    in such case the symbol should fallback to the form `CL{tick}-{token0}/{token1}`."""
    def mock_contract(*args, **kwargs):  # pylint: disable=unused-argument
        return MockEvmContract()

    with patch('rotkehlchen.chain.evm.contracts.EvmContracts.contract', mock_contract):
        query_velodrome_like_data(
            inquirer=optimism_inquirer,
            cache_type=CacheType.VELODROME_POOL_ADDRESS,
            msg_aggregator=optimism_inquirer.database.msg_aggregator,
            reload_all=False,
        )

    assert EvmToken('eip155:10/erc20:0x3241738149B24C9164dA14Fa2040159FFC6Dd237').symbol == 'CL10-USDC/MAI'  # noqa: E501


@pytest.mark.vcr
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
            write_cursor.execute('DELETE FROM general_cache WHERE value=?', (pool,))
            write_cursor.execute(f"DELETE FROM unique_cache WHERE key LIKE '%{pool}%'")

    assert not read_convex_data_from_cache()[0].items() & convex_expected_pools

    ethereum_inquirer.ensure_cache_data_is_updated(
        cache_type=CacheType.CONVEX_POOL_ADDRESS,
        query_method=query_convex_data,
        force_refresh=True,
    )  # populates convex caches
    assert len(read_convex_data_from_cache()[0].items() & convex_expected_pools) == 4


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('use_curve_api', [True, False])
def test_curve_cache(rotkehlchen_instance, use_curve_api, globaldb):
    global_cursor = globaldb.conn.cursor()
    """Test curve pools fetching mechanism"""
    # Set initial cache data to check that it is gone after the cache update
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # Make sure that curve cache is clear of ethereum pools and expected addressbook entries
        write_cursor.execute("DELETE FROM unique_cache WHERE key LIKE 'CURVE_POOL_ADDRESS10x%'")
        for entry in CURVE_EXPECTED_ADDRESBOOK_ENTRIES_FROM_CHAIN:
            write_cursor.execute('DELETE FROM address_book WHERE address=?', (entry.address,))

        # Ensure addresses for optimism (chain id 10 + 0x of address) are present. Regression test
        # for a problem where the 0x wasn't included and chain id 1 would also match chain id 10.
        assert write_cursor.execute(
            "SELECT COUNT(*) FROM unique_cache WHERE key LIKE 'CURVE_POOL_ADDRESS100x%'",
        ).fetchone()[0] > 0

    # delete one of the tokens to check that it is created during the update
    token_id = evm_address_to_identifier(
        address='0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811',  # aUSDT
        chain_id=ChainID.ETHEREUM,
    )
    with suppress(InputError):  # token may not exist but we don't care
        GlobalDBHandler().delete_asset_by_identifier(token_id)
    AssetResolver().clean_memory_cache(token_id)

    # Check the pools, coins and addresses from addressbook have been properly cleared
    pools, gauges = read_curve_pools_and_gauges(chain_id=ChainID.ETHEREUM)
    for pool in CURVE_EXPECTED_LP_TOKENS_TO_POOLS.values():
        assert pool not in pools
    for pool in CURVE_EXPECTED_POOL_COINS:
        assert pool not in pools
    assert len(gauges & CURVE_EXPECTED_GAUGES) == 0
    assert GlobalDBHandler().get_evm_token(
        address='0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811',
        chain_id=ChainID.ETHEREUM,
    ) is None

    for entry in CURVE_EXPECTED_ADDRESBOOK_ENTRIES_FROM_CHAIN:
        assert not address_in_addressbook(entry.address, global_cursor)

    ethereum_inquirer = rotkehlchen_instance.chains_aggregator.ethereum.node_inquirer
    curve_address_provider = ethereum_inquirer.contracts.contract(CURVE_ADDRESS_PROVIDER)

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
        curve_api_url = CURVE_API_URL.format(curve_blockchain_id=CURVE_CHAIN_ID[ChainID.ETHEREUM])
        assert url == curve_api_url, f'Unexpected url {url} was called'
        if use_curve_api is False:
            return MockResponse(status_code=200, text=json.dumps({'success': False, 'data': {'poolData': []}}))  # noqa: E501

        response_json = requests_get(url).json()
        response_json['data']['poolData'] = response_json['data']['poolData'][:2]
        return MockResponse(status_code=200, text=json.dumps(response_json))

    requests_patch = patch('requests.get', side_effect=mock_requests_get)
    notify_patch = patch.object(ethereum_inquirer.database.msg_aggregator, 'add_message')

    future_timestamp = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=WEEK_IN_SECONDS)  # noqa: E501
    with freeze_time(future_timestamp), requests_patch, call_contract_patch, notify_patch as mock_notify:  # noqa: E501
        rotkehlchen_instance.chains_aggregator.ethereum.assure_curve_cache_is_queried_and_decoder_updated(
            node_inquirer=ethereum_inquirer,
            transactions_decoder=rotkehlchen_instance.chains_aggregator.ethereum.transactions_decoder,
        )

    pools, gauges = read_curve_pools_and_gauges(chain_id=ChainID.ETHEREUM)
    for pool in CURVE_EXPECTED_LP_TOKENS_TO_POOLS.values():
        assert pool in pools
    for pool, pool_coins in CURVE_EXPECTED_POOL_COINS.items():
        assert pools.get(pool) == pool_coins
    assert len(gauges & CURVE_EXPECTED_GAUGES) == 2

    # Check that the token was created
    token = GlobalDBHandler().get_evm_token(
        address='0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811',
        chain_id=ChainID.ETHEREUM,
    )
    assert token.name == 'Aave interest bearing USDT'
    assert token.symbol == 'aUSDT'
    assert token.decimals == 6

    expected_addresses = CURVE_EXPECTED_ADDRESBOOK_ENTRIES_FROM_API if use_curve_api else CURVE_EXPECTED_ADDRESBOOK_ENTRIES_FROM_CHAIN  # noqa: E501
    for entry in expected_addresses:
        assert address_in_addressbook(entry.address, global_cursor)

    assert mock_notify.call_args_list == [
        make_call_object(CPT_CURVE, ChainID.ETHEREUM, processed=1, total=2),
    ] if use_curve_api else [
        make_call_object(CPT_CURVE, ChainID.ETHEREUM, processed=0, total=0),
        make_call_object(CPT_CURVE, ChainID.ETHEREUM, processed=1, total=2),
        make_call_object(CPT_CURVE, ChainID.ETHEREUM, processed=0, total=0),
        make_call_object(CPT_CURVE, ChainID.ETHEREUM, processed=1, total=2),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_gearbox_cache(ethereum_inquirer: EthereumInquirer):
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # make sure that gearbox cache is clear of expected pools and gauges
        for pool in GEARBOX_SOME_EXPECTED_POOLS:
            write_cursor.execute(f"DELETE FROM general_cache WHERE value LIKE '%{pool}%'")
            write_cursor.execute(f"DELETE FROM unique_cache WHERE key LIKE '%{pool}%'")

        for asset in GEARBOX_SOME_EXPECTED_ASSETS:
            write_cursor.execute(f"DELETE FROM assets WHERE identifier LIKE '%{asset}%'")

    pools, = read_gearbox_data_from_cache(ChainID.ETHEREUM)
    assert not pools.keys() & GEARBOX_SOME_EXPECTED_POOLS

    def mock_gearbox_pool_tokens(*args, **kwargs):
        if (tokens := get_gearbox_pool_tokens(*args, **kwargs)) is None:
            return None
        return sorted(tokens)  # sorted for determinism in VCR

    notify_patch = patch.object(ethereum_inquirer.database.msg_aggregator, 'add_message')
    get_gearbox_pool_tokens_patch = patch(
        target='rotkehlchen.chain.evm.decoding.gearbox.gearbox_cache.get_gearbox_pool_tokens',
        new=mock_gearbox_pool_tokens,
    )
    with get_gearbox_pool_tokens_patch, notify_patch as mock_notify:
        ethereum_inquirer.ensure_cache_data_is_updated(
            cache_type=CacheType.GEARBOX_POOL_ADDRESS,
            query_method=query_gearbox_data,
            chain_id=ChainID.ETHEREUM,
        )  # populates cache and assets tables
    pools, = read_gearbox_data_from_cache(ChainID.ETHEREUM)
    assert pools.keys() >= GEARBOX_SOME_EXPECTED_POOLS

    # Check that the count of pools in the DB matches the total count of raw pool data from onchain
    assert len(pools) == len(ethereum_inquirer.contracts.contract(
        CHAIN_ID_TO_DATA_COMPRESSOR[ethereum_inquirer.chain_id],
    ).call(node_inquirer=ethereum_inquirer, method_name='getPoolsV3List'))

    # Check tokens and pool data for both a pool with farming/lp tokens and one without.
    assert (usdc_pool := GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0xda00000035fef4082F78dEF6A8903bee419FbF8E'),
        chain_id=ChainID.ETHEREUM,
    )) is not None
    assert len(usdc_pool.underlying_tokens) == 1
    assert usdc_pool.underlying_tokens[0].address == string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')  # noqa: E501
    assert pools[usdc_pool.evm_address] == GearboxPoolData(
        pool_address=usdc_pool.evm_address,
        pool_name='Trade USDC v3',
        farming_pool_token='eip155:1/erc20:0x9ef444a6d7F4A5adcd68FD5329aA5240C90E14d2',
        lp_tokens={
            'eip155:1/erc20:0xc411dB5f5Eb3f7d552F9B8454B2D74097ccdE6E3',
            'eip155:1/erc20:0xda00000035fef4082F78dEF6A8903bee419FbF8E',
        },
    )
    assert (dola_pool := GlobalDBHandler.get_evm_token(
        address=string_to_evm_address('0x31426271449F60d37Cc5C9AEf7bD12aF3BdC7A94'),
        chain_id=ChainID.ETHEREUM,
    )) is not None
    assert len(dola_pool.underlying_tokens) == 1
    assert dola_pool.underlying_tokens[0].address == string_to_evm_address('0x865377367054516e17014CcdED1e7d814EDC9ce4')  # noqa: E501
    assert pools[dola_pool.evm_address] == GearboxPoolData(
        pool_address=dola_pool.evm_address,
        pool_name='Trade DOLA v3',
        farming_pool_token=None,
        lp_tokens=set(),
    )

    assert mock_notify.call_args_list == [
        make_call_object(CPT_GEARBOX, ChainID.ETHEREUM, processed=0, total=0),
        make_call_object(CPT_GEARBOX, ChainID.ETHEREUM, processed=1, total=8),
    ]


@pytest.mark.parametrize('optimism_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('number_of_eth_accounts', [1])
def test_reload_cache_timestamps(blockchain: ChainsAggregator, freezer):
    """Ensure that if we don't have new data the cache for curve updates the last queried ts"""
    freezer.move_to(
        datetime.datetime(year=2024, month=9, day=25, hour=15, minute=30, tzinfo=datetime.UTC),
    )
    assert should_update_protocol_cache(
        userdb=blockchain.database,
        cache_key=CacheType.CURVE_LP_TOKENS,
        args=(str(ChainID.ETHEREUM.serialize_for_db()),),
    ) is True

    curve = cast(
        'ReloadableDecoderMixin',
        blockchain.ethereum.transactions_decoder.decoders['Curve'],
    )
    with patch(
        'rotkehlchen.chain.evm.decoding.curve.curve_cache._query_curve_data_from_api',
        new=MagicMock(return_value=[]),
    ):
        curve.reload_data()

    freezer.move_to(
        datetime.datetime(year=2024, month=9, day=26, hour=15, minute=30, tzinfo=datetime.UTC),
    )
    assert should_update_protocol_cache(
        userdb=blockchain.database,
        cache_key=CacheType.CURVE_LP_TOKENS,
        args=(str(ChainID.ETHEREUM.serialize_for_db()),),
    ) is False


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_balancer_cache(ethereum_inquirer):
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # make sure that balancer cache is clear of expected pools and gauges
        for pool in BALANCER_SOME_EXPECTED_POOLS | BALANCER_SOME_EXPECTED_GAUGES:
            write_cursor.execute(f"DELETE FROM general_cache WHERE value LIKE '%{pool}%'")
            write_cursor.execute('DELETE FROM address_book WHERE address=?', (pool,))

    pools, gauges = read_balancer_pools_and_gauges_from_cache(
        version=2,
        chain_id=ethereum_inquirer.chain_id,
        cache_type=CacheType.BALANCER_V2_POOLS,
    )
    assert not pools & BALANCER_SOME_EXPECTED_POOLS
    assert not gauges & BALANCER_SOME_EXPECTED_GAUGES

    ethereum_inquirer.ensure_cache_data_is_updated(
        cache_type=CacheType.BALANCER_V2_POOLS,
        query_method=lambda inquirer, cache_type, msg_aggregator, reload_all: query_balancer_data(
            inquirer=inquirer,
            cache_type=cache_type,
            protocol=CPT_BALANCER_V2,
            msg_aggregator=msg_aggregator,
            version=2,
            reload_all=reload_all,
        ),
    )
    pools, gauges = read_balancer_pools_and_gauges_from_cache(
        version=2,
        chain_id=ethereum_inquirer.chain_id,
        cache_type=CacheType.BALANCER_V2_POOLS,
    )
    assert pools >= BALANCER_SOME_EXPECTED_POOLS
    assert gauges >= BALANCER_SOME_EXPECTED_GAUGES


@pytest.mark.vcr
def test_query_balancer_data_protocol_version_gnosis(gnosis_inquirer):
    """Test that query_balancer_data correctly sets the protocol version for tokens."""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM evm_tokens WHERE address=?', (pool_address := string_to_evm_address('0xBc2acf5E821c5c9f8667A36bB1131dAd26Ed64F9'),)).fetchone()[0] == 0  # noqa: E501

    query_balancer_data(
        version=2,
        inquirer=gnosis_inquirer,
        msg_aggregator=gnosis_inquirer.database.msg_aggregator,
        protocol=CPT_BALANCER_V2,
        cache_type=CacheType.BALANCER_V2_POOLS,
        reload_all=True,
    )

    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert cursor.execute('SELECT protocol FROM evm_tokens WHERE address=?', (pool_address,)).fetchone()[0] == 'balancer-v2'  # noqa: E501


@pytest.mark.vcr
def test_query_beefy_legacy_boosts(ethereum_inquirer: 'EthereumInquirer') -> None:
    """Test that query_beefy_vaults correctly creates legacy boost tokens."""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM evm_tokens WHERE protocol=?', (CPT_BEEFY_FINANCE,)).fetchone()[0] == 0  # noqa: E501

    def mock_request_get(url: str, *args, **kwargs):
        if 'vaults/all/1' in url:
            return []
        elif 'boosts/ethereum' in url:
            return [{'version': 1, 'poolId': 'curve-shezeth-eth', 'earnContractAddress': '0xbd313b13ed794B86Bd161885F8e170769E0e68b2', 'tokenAddress': '0x46EA5993fdDC27E4f770eFfB6921F401101Cbd59'}, {'version': 1, 'poolId': 'silo-weeth-eth', 'earnContractAddress': '0xC0dD9F05511Eec7f3C9C755816E4A25caECde47a', 'tokenAddress': '0x0E5F3a47122901D3eE047d2C7e1B36b419Ede5FE'}]  # noqa: E501
        raise ValueError(f'Unexpected URL: {url}')

    with patch('rotkehlchen.chain.evm.decoding.beefy_finance.utils.request_get', side_effect=mock_request_get):  # noqa: E501
        query_beefy_vaults(evm_inquirer=ethereum_inquirer)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT a.name, cad.symbol, et.decimals FROM evm_tokens et '
            'JOIN assets a ON et.identifier = a.identifier '
            'JOIN common_asset_details cad ON a.identifier = cad.identifier '
            'WHERE et.protocol = ?',
            (CPT_BEEFY_FINANCE,),
        ).fetchall() == [
            ('Reward Moo Curve ShezETH-ETH', 'rmooCurveShezETH-ETH', 18),
            ('Reward Moo Silo WETH (weETH Market)', 'rmooSiloWETH', 18),
        ]


def test_superfluid_cache(ethereum_inquirer: EthereumInquirer):
    """Test that the superfluid super tokens are created correctly"""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM evm_tokens WHERE protocol=?', (CPT_SUPERFLUID,)).fetchone()[0] == 0  # noqa: E501

    def mock_request_get(url: str, *args, **kwargs):
        if 'superfluid-org/tokenlist' in url:
            return json.loads('{"name":"Superfluid Token List","timestamp":"2025-11-04T19:21:20.148Z","version":{"major":5,"minor":35,"patch":0},"tokens":[{"chainId":1,"address":"0x1ba8603da702602a8657980e825a6daa03dee93a","name":"Super USD Coin","symbol":"USDCx","decimals":18,"logoURI":"https://tokenlist.superfluid.org/icons/usdc.svg","tags":["supertoken"],"extensions":{"orderingScore":380,"superTokenInfo":{"type":"Wrapper","underlyingTokenAddress":"0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"}}},{"chainId":1,"address":"0xc22bea0be9872d8b7b3933cec70ece4d53a900da","name":"Super ETH","symbol":"ETHx","decimals":18,"logoURI":"https://tokenlist.superfluid.org/icons/eth.svg","tags":["supertoken"],"extensions":{"orderingScore":319,"superTokenInfo":{"type":"Native Asset"}}},{"chainId":56,"address":"0x529a4116f160c833c61311569d6b33dff41fd657","name":"Super BNB","symbol":"BNBx","decimals":18,"logoURI":"https://tokenlist.superfluid.org/icons/bnb.svg","tags":["supertoken"],"extensions":{"orderingScore":429,"superTokenInfo":{"type":"Native Asset"}}},{"chainId":1,"address":"0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48","name":"USD Coin","symbol":"USDC","decimals":6,"logoURI":"https://tokenlist.superfluid.org/icons/usdc.svg","tags":["underlying"]}]}')  # noqa: E501

        raise ValueError(f'Unexpected request: {url}')

    with patch('rotkehlchen.chain.evm.decoding.superfluid.utils.request_get_dict', side_effect=mock_request_get):  # noqa: E501
        query_superfluid_tokens(evm_inquirer=ethereum_inquirer)

    # Check that both ethereum super tokens are present
    assert (usdcx := get_evm_token(
        evm_address=string_to_evm_address('0x1ba8603da702602a8657980e825a6daa03dee93a'),
        chain_id=ChainID.ETHEREUM,
    )) is not None
    assert usdcx.protocol == CPT_SUPERFLUID
    assert usdcx.name == 'Super USD Coin'
    assert usdcx.symbol == 'USDCx'
    assert (ethx := get_evm_token(
        evm_address=string_to_evm_address('0xc22bea0be9872d8b7b3933cec70ece4d53a900da'),
        chain_id=ChainID.ETHEREUM,
    )) is not None
    assert ethx.protocol == CPT_SUPERFLUID
    assert ethx.name == 'Super ETH'
    assert ethx.symbol == 'ETHx'
    # Check that the supertoken on BSC was not processed
    assert get_evm_token(
        evm_address=string_to_evm_address('0x529a4116f160c833c61311569d6b33dff41fd657'),
        chain_id=ChainID.BINANCE_SC,
    ) is None

    # Check that querying again doesn't try to process tokens since the cached version is the same.
    with (
        patch('rotkehlchen.chain.evm.decoding.superfluid.utils.request_get_dict', side_effect=mock_request_get),  # noqa: E501
        patch('rotkehlchen.chain.evm.decoding.superfluid.utils.get_or_create_evm_token') as create_token_mock,  # noqa: E501
    ):
        query_superfluid_tokens(evm_inquirer=ethereum_inquirer)

    assert create_token_mock.call_count == 0
