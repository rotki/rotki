import random
from typing import TYPE_CHECKING, Any
from unittest.mock import _patch, patch

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.externalapis.etherscan import Etherscan

LQTY_ADDR = string_to_evm_address('0x063c26fF1592688B73d8e2A18BA4C23654e2792E')
LQTY_PROXY = string_to_evm_address('0x9476832d4687c14b2c1a04E2ee4693162a7340B6')
ADDR_WITHOUT_TROVE = string_to_evm_address('0xA0446D8804611944F1B527eCD37d7dcbE442caba')
JUSTIN = string_to_evm_address('0x3DdfA8eC3052539b6C9549F12cEA2C295cfF5296')
LIQUITY_POOL_DEPOSITOR = string_to_evm_address('0xFBcAFB005695afa660836BaC42567cf6917911ac')


def make_liquity_proxy_patch(
        user_address: ChecksumEvmAddress,
        proxy_address: ChecksumEvmAddress,
) -> _patch:
    """Helper function to patch the liquity proxy detection after https://github.com/rotki/rotki/pull/11038
    to avoid needing to re-record VCRs on tests where the tested addresses no longer have the
    balances etc that are being tested.
    """
    return patch(
        target='rotkehlchen.chain.evm.proxies_inquirer.EvmProxiesInquirer.get_or_query_liquity_proxy',
        return_value={user_address: {proxy_address}},
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[LQTY_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_trove_position(rotkehlchen_api_server: APIServer, inquirer: Inquirer) -> None:  # pylint: disable=unused-argument
    """Test that we can get the status of the user's troves"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'liquitytrovesresource',
    ), json={'async_query': async_query})
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    assert LQTY_ADDR in result['balances']
    assert 'balances' in result
    assert 'total_collateral_ratio' in result
    assert result['total_collateral_ratio'] == '0.2797543579772264'

    balances = result['balances']

    assert balances == {
        '0x063c26fF1592688B73d8e2A18BA4C23654e2792E': {
            'collateral': {
                'amount': '0',
                'value': '0.0',
                'usd_value': '0',
                'asset': 'ETH',
            },
            'debt': {
                'amount': '0',
                'value': '0.0',
                'usd_value': '0',
                'asset': 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0',
            },
            'collateralization_ratio': None,
            'liquidation_price': None,
            'active': True,
            'trove_id': 148,
        },
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd5B94F452a9B1D69fAe2DF3812F9FE22fa52094f']])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_trove_staking(rotkehlchen_api_server: APIServer, inquirer: Inquirer, ethereum_accounts: list[ChecksumEvmAddress]) -> None:  # pylint: disable=unused-argument  # noqa: E501
    """Test that we can get the status of the staked lqty"""
    async_query = random.choice([False, True])
    with make_liquity_proxy_patch(
        user_address=ethereum_accounts[0],
        proxy_address=string_to_evm_address('0xD29d5Db21CD29BC5aA35FB071a0d5E3526b513BC'),
    ):
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'liquitystakingresource',
        ), json={'async_query': async_query})

    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    assert (user := ethereum_accounts[0]) in result
    stake_data = result[user]
    assert stake_data == {
        'balances': {
            'staked': {
                'asset': A_LQTY.identifier,
                'amount': '613.102214311218459876',
                'usd_value': '0',
                'value': '919.6533214668276898140',
            },
            'lusd_rewards': {
                'asset': A_LUSD.identifier,
                'amount': '0.031242621411895105',
                'usd_value': '0',
                'value': '0.0468639321178426575',
            },
            'eth_rewards': {
                'asset': A_ETH.identifier,
                'amount': '0.000036437529327527',
                'usd_value': '0',
                'value': '0.0000546562939912905',
            },
        },
        'proxies': {
            '0xD29d5Db21CD29BC5aA35FB071a0d5E3526b513BC': {
                'eth_rewards': {'amount': '0', 'asset': 'ETH', 'usd_value': '0', 'value': '0.0'},
                'lusd_rewards': {
                    'amount': '0',
                    'asset': 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0',
                    'usd_value': '0',
                    'value': '0.0',
                },
                'staked': {
                    'amount': '0',
                    'asset': 'eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D',
                    'usd_value': '0',
                    'value': '0.0',
                },
            },
        },
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDR_WITHOUT_TROVE]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_account_without_info(rotkehlchen_api_server: APIServer, inquirer: Inquirer) -> None:  # pylint: disable=unused-argument
    """Test that we can get the status of the trove and the staked lqty"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'liquitytrovesresource',
    ), json={'async_query': async_query})
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    assert 'balances' in result
    assert 'total_collateral_ratio' in result
    assert result['total_collateral_ratio'] == '0.2797543579772264'

    balances = result['balances']
    assert isinstance(balances, dict)

    assert ADDR_WITHOUT_TROVE not in balances


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[LQTY_PROXY, ADDR_WITHOUT_TROVE, LQTY_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_account_with_proxy(rotkehlchen_api_server: APIServer, inquirer: Inquirer) -> None:  # pylint: disable=unused-argument
    """Test that we can get the status of a trove created using DSProxy"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'liquitytrovesresource',
    ), json={'async_query': async_query})
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    assert 'balances' in result
    assert 'total_collateral_ratio' in result
    assert result['total_collateral_ratio'] == '0.2797543579772264'

    balances = result['balances']
    assert isinstance(balances, dict)

    assert LQTY_PROXY in balances
    assert ADDR_WITHOUT_TROVE not in balances
    assert LQTY_ADDR in balances

    assert balances == {
        '0x063c26fF1592688B73d8e2A18BA4C23654e2792E': {
            'collateral': {
                'amount': '0',
                'value': '0.0',
                'usd_value': '0',
                'asset': 'ETH',
            },
            'debt': {
                'amount': '0',
                'value': '0.0',
                'usd_value': '0',
                'asset': 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0',
            },
            'collateralization_ratio': None,
            'liquidation_price': None,
            'active': True,
            'trove_id': 148,
        },
        '0x9476832d4687c14b2c1a04E2ee4693162a7340B6': {
            'collateral': {
                'amount': '0',
                'value': '0.0',
                'usd_value': '0',
                'asset': 'ETH',
            },
            'debt': {
                'amount': '0',
                'value': '0.0',
                'usd_value': '0',
                'asset': 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0',
            },
            'collateralization_ratio': None,
            'liquidation_price': None,
            'active': True,
            'trove_id': 267,
        },
    }
    # test that the list of addresses was not mutated
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert len(rotki.chains_aggregator.accounts.eth) == 3


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4E61768814dFD25C2310db372FBA377c1848cd52']])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_staking_v2_with_liquity_proxy(rotkehlchen_api_server: APIServer, ethereum_accounts: list[ChecksumEvmAddress], inquirer: Inquirer) -> None:  # pylint: disable=unused-argument  # noqa: E501
    """Test that we get staking balance, staked using the new liquity proxy in v2 staking"""
    async_query = random.choice([False, True])
    with make_liquity_proxy_patch(
        user_address=(user := ethereum_accounts[0]),
        proxy_address=(proxy := string_to_evm_address('0x1CA64c0DC9194c6635e1c14C14B795be04833AEC')),  # noqa: E501
    ):
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'liquitystakingresource',
        ), json={'async_query': async_query})

    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )
    assert result[user]['balances']['staked']['amount'] == '0'
    assert result[user]['balances']['eth_rewards']['amount'] == '0'
    assert result[user]['balances']['lusd_rewards']['amount'] == '0'
    assert result[user]['proxies'][proxy]['staked']['amount'] == '104.48'
    assert result[user]['proxies'][proxy]['staked']['asset'] == A_LQTY.identifier  # liquity # noqa: E501
    assert result[user]['proxies'][proxy]['eth_rewards']['amount'] == '0.000006209393760577'
    assert result[user]['proxies'][proxy]['lusd_rewards']['amount'] == '0.002367116256741337'


@pytest.mark.parametrize('ethereum_accounts', [[JUSTIN, LIQUITY_POOL_DEPOSITOR]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_stability_pool(rotkehlchen_api_server: APIServer) -> None:
    """Test that we can get the status of the deposits in the stability pool"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    eth_multicall = rotki.chains_aggregator.ethereum.node_inquirer.contracts.contract(string_to_evm_address('0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696'))  # noqa: E501

    def mock_etherscan_transaction_response(etherscan: 'Etherscan') -> _patch:
        def mocked_request_dict(url: str, params: dict[str, str], *_args: Any, **_kwargs: Any) -> MockResponse:  # noqa: E501
            # if '0xeefBa1e63905eF1D7ACbA5a8513c70307C1cE441' in url:
            if params.get('to') == eth_multicall.address:
                if (data := params.get('data', '')).startswith('0x252dba42'):  # aggregate
                    payload = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000000000000f1d3ed00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000"}'  # noqa: E501
                elif data.startswith('0xbce38bd7'):  # tryAggregate
                    payload = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000014000000000000000000000000000000000000000000000000000000000000001c0000000000000000000000000000000000000000000000000000000000000024000000000000000000000000000000000000000000000000000000000000002c000000000000000000000000000000000000000000000000000000000000003400000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000025741350d10dcdd3f00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000182ca8387c1e947389a80000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000872593255709e930eb1b7000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000002d94f2ad87a21c00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000008737d8d1f366513ff80000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000073bcd36975544d15f2be"}'  # noqa: E501
            else:
                raise AssertionError('Got in unexpected section during test')
            return MockResponse(200, payload)
        return patch.object(etherscan.session, 'get', wraps=mocked_request_dict)

    async_query = random.choice([False, True])
    with mock_etherscan_transaction_response(rotki.chains_aggregator.ethereum.node_inquirer.etherscan):  # noqa: E501
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'liquitystabilitypoolresource',
        ), json={'async_query': async_query})

    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    assert JUSTIN in result
    assert LIQUITY_POOL_DEPOSITOR in result
    expected_amount = FVal('43.180853032438783295')
    assert result[JUSTIN]['balances']['gains']['asset'] == A_ETH
    assert FVal(result[JUSTIN]['balances']['gains']['amount']) == expected_amount
    assert FVal(result[JUSTIN]['balances']['gains']['value']) == expected_amount * FVal(1.5)
    expected_amount = FVal('114160.573902982554552744')
    assert result[JUSTIN]['balances']['rewards']['asset'] == A_LQTY
    assert FVal(result[JUSTIN]['balances']['rewards']['amount']) == expected_amount
    assert FVal(result[JUSTIN]['balances']['rewards']['value']) == expected_amount * FVal(1.5)
    expected_amount = FVal('10211401.723115634393264567')
    assert result[JUSTIN]['balances']['deposited']['asset'] == A_LUSD
    assert FVal(result[JUSTIN]['balances']['deposited']['amount']) == expected_amount
    assert FVal(result[JUSTIN]['balances']['deposited']['value']) == expected_amount * FVal(1.5)


@pytest.mark.parametrize('new_db_unlock_actions', [None])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('add_accounts_to_db', [[False]])
@pytest.mark.parametrize('ethereum_accounts', [
    [
        '0xF662f831361c8Ab48d807f7753eb3d641be25d24',
        '0xbB8311c7bAD518f0D8f907Cad26c5CcC85a06dC4',
    ],
])
def test_staking_stats(rotkehlchen_api_server: APIServer, ethereum_accounts: list[str]) -> None:
    """
    Test that the stats generated by the liquity endpoint are correct using mocked events
    and that the stats combining all the data are consistent with the
    information for each tracked address
    """
    default_ts = TimestampMS(1707278951000)
    reward_lusd_event = make_evm_tx_hash()
    evm_events = [
        EvmEvent(  # deposit 1 for address 0
            tx_ref=make_evm_tx_hash(),
            sequence_index=1,
            timestamp=default_ts,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LUSD,
            amount=FVal('1974'),
            counterparty=CPT_LIQUITY,
            location_label=ethereum_accounts[0],
        ), EvmEvent(  # deposit 2 for address 0
            tx_ref=make_evm_tx_hash(),
            sequence_index=1,
            timestamp=default_ts,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LUSD,
            amount=FVal('2000'),
            counterparty=CPT_LIQUITY,
            location_label=ethereum_accounts[0],
        ), EvmEvent(  # deposit 1 for address 1
            tx_ref=make_evm_tx_hash(),
            sequence_index=1,
            timestamp=default_ts,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LUSD,
            amount=FVal('1000'),
            counterparty=CPT_LIQUITY,
            location_label=ethereum_accounts[1],
        ), EvmEvent(  # address 0 stability pool gains
            tx_ref=make_evm_tx_hash(),
            sequence_index=1,
            timestamp=default_ts,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LQTY,
            amount=FVal(44),
            counterparty=CPT_LIQUITY,
            location_label=ethereum_accounts[0],
        ), EvmEvent(  # address 1 stability pool gains
            tx_ref=make_evm_tx_hash(),
            sequence_index=1,
            timestamp=default_ts,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LQTY,
            amount=FVal(4240.34942308358),
            counterparty=CPT_LIQUITY,
            location_label=ethereum_accounts[1],
        ), EvmEvent(  # stake lqty and get reward
            tx_ref=reward_lusd_event,
            sequence_index=1,
            timestamp=default_ts,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LQTY,
            amount=FVal(10),
            counterparty=CPT_LIQUITY,
            location_label=ethereum_accounts[1],
        ), EvmEvent(
            tx_ref=reward_lusd_event,
            sequence_index=2,
            timestamp=default_ts,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LUSD,
            amount=FVal(65556),
            counterparty=CPT_LIQUITY,
            location_label=ethereum_accounts[1],
        ), EvmEvent(  # lqty reward for address 0
            tx_ref=make_evm_tx_hash(),
            sequence_index=2,
            timestamp=default_ts,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LQTY,
            amount=FVal(400),
            counterparty=CPT_LIQUITY,
            location_label=ethereum_accounts[0],
        ),
    ]
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    history_events = DBHistoryEvents(db)
    with db.user_write() as write_cursor:
        for event in evm_events:
            history_events.add_history_event(
                write_cursor=write_cursor,
                event=event,
            )

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'modulestatsresource',
        module='liquity',
    ), json={'async_query': False})
    result = assert_proper_sync_response_with_result(response)

    global_stats = result['global_stats']
    address_0_data = result['by_address'][ethereum_accounts[0]]
    address_1_data = result['by_address'][ethereum_accounts[1]]
    assert FVal(address_0_data['total_deposited_stability_pool']) == FVal('3974')
    assert FVal(address_1_data['total_deposited_stability_pool']) == FVal('1000')
    assert FVal(global_stats['total_deposited_stability_pool']) == FVal(address_0_data['total_deposited_stability_pool']) + FVal(address_1_data['total_deposited_stability_pool'])  # noqa: E501
    assert address_0_data['stability_pool_gains'][0]['amount'] == '444'
    assert address_1_data['stability_pool_gains'][0]['amount'] == '4240.34942308358'
    assert len(global_stats['staking_gains']) == 1
    assert len(global_stats['stability_pool_gains']) == 1
    assert FVal(global_stats['stability_pool_gains'][0]['amount']).is_close(FVal(address_0_data['stability_pool_gains'][0]['amount']) + FVal(address_1_data['stability_pool_gains'][0]['amount']), max_diff='1e-8')  # noqa: E501


@pytest.mark.vcr(match_on=['uri', 'method'], filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD77Eb80F38fEC10D87A192d07329415173307E93']])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_proxy_info_is_shown(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Check that information about proxies is added to the responses for liquity endpoints"""
    with make_liquity_proxy_patch(
        user_address=(user_address := ethereum_accounts[0]),
        proxy_address=(proxy_address := string_to_evm_address('0x3Dd5BbB839f8AE9B64c73780e89Fdd1181Bf5205')),  # noqa: E501
    ):
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'liquitystabilitypoolresource',
        ), json={'async_query': False})

        result = assert_proper_sync_response_with_result(response)
        assert 'gains' in result[user_address]['proxies'][proxy_address]

        # check the other endpoint.
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'liquitystakingresource',
        ), json={'async_query': False})
        result = assert_proper_sync_response_with_result(response)
        assert 'staked' in result[user_address]['proxies'][proxy_address]
