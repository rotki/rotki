import datetime
import json
from contextlib import suppress
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, _Call, call, patch

import pytest
import requests
from freezegun import freeze_time

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.ethereum.modules.convex.convex_cache import (
    query_convex_data,
    read_convex_data_from_cache,
)
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.decoding.curve.constants import (
    CPT_CURVE,
    CURVE_ADDRESS_PROVIDER,
    CURVE_API_URL,
    CURVE_CHAIN_ID,
)
from rotkehlchen.chain.evm.decoding.curve.curve_cache import read_curve_pools_and_gauges
from rotkehlchen.chain.evm.decoding.gearbox.constants import CPT_GEARBOX
from rotkehlchen.chain.evm.decoding.gearbox.gearbox_cache import (
    get_gearbox_pool_tokens,
    query_gearbox_data,
    read_gearbox_data_from_cache,
)
from rotkehlchen.chain.evm.decoding.interfaces import ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_VELODROME
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    query_velodrome_like_data,
    read_velodrome_pools_and_gauges_from_cache,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.filtering import AddressbookFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    AddressbookEntry,
    CacheType,
    ChainID,
    EvmTokenKind,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer


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
    'eip155:10/erc20:0x8134A2fDC127549480865fB8E5A9E8A8a95a54c5',
    'eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
    'eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607',
]

GEARBOX_SOME_EXPECTED_POOLS = {
    string_to_evm_address('0xda00000035fef4082F78dEF6A8903bee419FbF8E'),
    string_to_evm_address('0xda00010eDA646913F273E10E7A5d1F659242757d'),
    string_to_evm_address('0xda0002859B2d05F66a753d8241fCDE8623f26F4f'),
    string_to_evm_address('0x1DC0F3359a254f876B37906cFC1000A35Ce2d717'),
}

GEARBOX_SOME_EXPECTED_ASSETS = [
    'eip155:1/erc20:0xda00000035fef4082F78dEF6A8903bee419FbF8E',
    'eip155:1/erc20:0xc411dB5f5Eb3f7d552F9B8454B2D74097ccdE6E3',
    'eip155:1/erc20:0xe753260F1955e8678DCeA8887759e07aa57E8c54',
    'eip155:1/erc20:0xda00010eDA646913F273E10E7A5d1F659242757d',
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


def address_in_addressbook(address, cursor):
    return cursor.execute('SELECT address FROM address_book WHERE address=?', (address,)).fetchone() is not None  # noqa: E501


def make_call_object(protocol: str, chain: ChainID, processed: int, total: int) -> _Call:
    """Create a call object for the given protocol, chain, processed and total."""
    return call(
        message_type=WSMessageType.PROTOCOL_CACHE_UPDATES,
        data={
            'protocol': protocol,
            'chain': chain,
            'processed': processed,
            'total': total,
        },
    )


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

    notify_patch = patch.object(optimism_inquirer.database.msg_aggregator, 'add_message')
    with notify_patch as mock_notify:
        optimism_inquirer.ensure_cache_data_is_updated(
            cache_type=CacheType.VELODROME_POOL_ADDRESS,
            query_method=query_velodrome_like_data,
        )  # populates cache, addressbook and assets tables
    pools, gauges = read_velodrome_pools_and_gauges_from_cache()
    assert pools >= VELODROME_SOME_EXPECTED_POOLS
    assert gauges >= VELODROME_SOME_EXPECTED_GAUGES
    addressbook_entries, asset_identifiers = get_velodrome_addressbook_and_asset_identifiers(optimism_inquirer)  # noqa: E501
    assert all(entry in addressbook_entries for entry in VELODROME_SOME_EXPECTED_ADDRESBOOK_ENTRIES)  # noqa: E501
    assert all((identifier,) in asset_identifiers for identifier in VELODROME_SOME_EXPECTED_ASSETS)

    assert mock_notify.call_args_list == [make_call_object(CPT_VELODROME, ChainID.OPTIMISM, 0, 0)]


class MockEvmContract:
    """A mock contract class that returns a desired result for a `call` function.
    Used for `test_velodrome_cache_with_no_symbol`."""
    def call(self, **kwargs):
        if kwargs['arguments'][1] == 0:
            return [{
                0: '0x3241738149B24C9164dA14Fa2040159FFC6Dd237',
                1: '',
                2: 18,
                4: 10,
                7: '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85',
                10: '0xdFA46478F9e5EA86d57387849598dbFB2e964b02',
                13: '0xBe3235e341393e43949aAd6F073982F67BFF412f',
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
            write_cursor.execute(f'DELETE FROM general_cache WHERE value="{pool}"')
            write_cursor.execute(f'DELETE FROM unique_cache WHERE key LIKE "%{pool}%"')

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
        # make sure that curve cache is clear of expected pools and addressbook entries
        for lp_token in CURVE_EXPECTED_LP_TOKENS_TO_POOLS:
            write_cursor.execute(f'DELETE FROM unique_cache WHERE key LIKE "%{lp_token}%"')
        for entry in CURVE_EXPECTED_ADDRESBOOK_ENTRIES_FROM_CHAIN:
            write_cursor.execute(f'DELETE FROM address_book WHERE address="{entry.address}"')

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
            write_cursor.execute(f'DELETE FROM general_cache WHERE value LIKE "%{pool}%"')
            write_cursor.execute(f'DELETE FROM address_book WHERE address="{pool}"')

        for asset in GEARBOX_SOME_EXPECTED_ASSETS:
            write_cursor.execute(f'DELETE FROM assets WHERE identifier LIKE "%{asset}%"')

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
        )  # populates cache, addressbook and assets tables
    pools, = read_gearbox_data_from_cache(ChainID.ETHEREUM)
    assert pools.keys() >= GEARBOX_SOME_EXPECTED_POOLS

    assert mock_notify.call_args_list == [
        make_call_object(CPT_GEARBOX, ChainID.ETHEREUM, processed=0, total=0),
        make_call_object(CPT_GEARBOX, ChainID.ETHEREUM, processed=1, total=5),
    ]


@pytest.mark.parametrize('optimism_accounts', [[make_evm_address()]])
@pytest.mark.parametrize('number_of_eth_accounts', [1])
def test_reload_cache_timestamps(blockchain: ChainsAggregator, freezer):
    """Ensure that if we don't have new data the cache for curve updates the last queried ts"""
    freezer.move_to(
        datetime.datetime(year=2024, month=9, day=25, hour=15, minute=30, tzinfo=datetime.UTC),
    )
    assert should_update_protocol_cache(
        cache_key=CacheType.CURVE_LP_TOKENS,
        args=(str(ChainID.ETHEREUM.serialize_for_db()),),
    ) is True

    curve = cast(
        ReloadableDecoderMixin,
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
        cache_key=CacheType.CURVE_LP_TOKENS,
        args=(str(ChainID.ETHEREUM.serialize_for_db()),),
    ) is False
