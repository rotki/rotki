from http import HTTPStatus

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.ethereum import SupportedBlockchain
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    ChainID,
    ChecksumEvmAddress,
    Location,
    TimestampMS,
)


@pytest.mark.vcr(match_on=['match_rpc_calls'])
@pytest.mark.parametrize('ethereum_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(WeightedNode(
    node_info=NodeName(  # set the node to make it deterministic
        name='merkle',
        endpoint='https://eth.merkle.io',
        owned=True,
        blockchain=SupportedBlockchain.ETHEREUM,
    ),
    active=True,
    weight=ONE,
),)])
def test_transfers(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_manager_connect_at_start: list[WeightedNode],
):
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    from_address, to_address = ethereum_accounts[0], string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306')  # noqa: E501

    with db.user_write() as write_cursor:
        DBHistoryEvents(db).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=1,
                timestamp=TimestampMS(0),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRANSFER,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal(0.5),
                location_label=from_address,
                notes=f'Transfer 0.5 ETH to {to_address}',
                address=to_address,
                identifier=None,
                extra_data=None,
            ),
            mapping_values=None,
        )

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'addressesinteractedresource'),
        json={'from_address': from_address, 'to_address': to_address},
    )
    assert assert_proper_sync_response_with_result(response) is True

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'preparetokentransferresource'),
        json={
            'from_address': from_address,
            'to_address': to_address,
            'token': 'eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',
            'amount': '0.000000000000000001',
        },
    )
    payload = assert_proper_sync_response_with_result(response)

    assert payload['from'] == ethereum_accounts[0]
    assert payload['to'] == '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
    assert payload['data'] == '0xa9059cbb0000000000000000000000009531c059098e3d194ff87febb587ab07b30b13060000000000000000000000000000000000000000000000000000000000000001'  # noqa: E501

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'preparenativetransferresource'),
        json={
            'from_address': from_address,
            'to_address': string_to_evm_address('0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2'),
            'amount': '0.0003',
            'chain': 'ethereum',
        },
    )

    payload = assert_proper_sync_response_with_result(response)
    assert payload == {
        'from': '0xc37b40ABdB939635068d3c5f13E7faF686F03B65',
        'to': '0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2',
        'value': 300000000000000,
        'nonce': 55,
    }

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'addressesinteractedresource'),
        json={
            'from_address': from_address,
            'to_address': string_to_evm_address('0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2'),
        },
    )
    assert assert_proper_sync_response_with_result(response) is False


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_token_balance(rotkehlchen_api_server: APIServer) -> None:
    accounts_to_query: list[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, str]] = [
        (ChainID.ETHEREUM, 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        (ChainID.GNOSIS, 'eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
        (ChainID.ARBITRUM_ONE, 'eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
        (ChainID.BASE, 'eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        (ChainID.BINANCE_SC, 'eip155:56/erc20:0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d'),
        (ChainID.OPTIMISM, 'eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
        (ChainID.POLYGON_POS, 'eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'),
        (ChainID.SCROLL, 'eip155:534352/erc20:0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4'),
    ]
    expected_balances: dict[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, tuple[FVal, FVal]] = {
        ChainID.ETHEREUM: (FVal('0.031539457397873656'), FVal('0.000009')),
        ChainID.GNOSIS: (FVal('0.849160883064293869'), ZERO),
        ChainID.ARBITRUM_ONE: (FVal('0.00399601731'), ZERO),
        ChainID.BASE: (FVal('0.061702767638680266'), ZERO),
        ChainID.BINANCE_SC: (ZERO, ZERO),
        ChainID.OPTIMISM: (FVal('0.294773308352668013'), ZERO),
        ChainID.POLYGON_POS: (FVal('51.956048192422479229'), FVal('23.755147')),
        ChainID.SCROLL: (ZERO, ZERO),
    }
    chain_aggregator = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator
    for chain, token_id in accounts_to_query:
        expected_native_balance, expected_token_balance = expected_balances[chain]
        native_token_response = requests.post(
            api_url_for(rotkehlchen_api_server, 'accounttokenbalanceresource'),
            json={
                'address': '0x9531C059098e3d194fF87FebB587aB07B30B1306',
                'evm_chain': (chain_name := chain.to_name()),
                'asset': chain_aggregator.get_evm_manager(chain).node_inquirer.native_token.identifier,  # noqa: E501
            },
        )
        assert FVal(assert_proper_sync_response_with_result(native_token_response)) == expected_native_balance  # noqa: E501

        erc20_response = requests.post(
            api_url_for(rotkehlchen_api_server, 'accounttokenbalanceresource'),
            json={
                'asset': token_id,
                'evm_chain': chain_name,
                'address': '0x9531C059098e3d194fF87FebB587aB07B30B1306',
            },
        )
        assert FVal(assert_proper_sync_response_with_result(erc20_response)) == expected_token_balance  # noqa: E501

    error_response = requests.post(
        api_url_for(rotkehlchen_api_server, 'accounttokenbalanceresource'),
        json={
            'asset': 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            'evm_chain': ChainID.OPTIMISM.to_name(),
            'address': '0x9531C059098e3d194fF87FebB587aB07B30B1306',
        },
    )
    assert_error_response(
        response=error_response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='Token exists on different chain than requested',
    )
