import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_sync_response_with_result
from rotkehlchen.tests.utils.ethereum import SupportedBlockchain
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS


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
                tx_hash=make_evm_tx_hash(),
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
