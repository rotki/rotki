from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.quickswap.constants import CPT_QUICKSWAP_V3
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_POLYGON_POS_MATIC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x1834E499eA7F6759992AAd97362D985AA2efa5fc']])
def test_swap(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x50c55589a2a7b97bdb0c46815783993133c8bd099d9fcc8b91e2e465f00f4687')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        timestamp=(timestamp := TimestampMS(1756239853000)),
        location=Location.POLYGON_POS,
        sequence_index=0,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_amount := '0.011052763177263014'),
        location_label=(user_address := polygon_pos_accounts[0]),
        notes=f'Burn {gas_amount} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=1,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:137/erc20:0xeB51D9A39AD5EEF215dC0Bf39a8821ff804A0F01'),
        amount=FVal(approval_amount := '115792089237316195423570985008687907853269984665640564039457584006926.433208663'),  # noqa: E501
        location_label=user_address,
        notes=f'Set LGNS spending approval of {user_address} by 0xf5b509bB0909a69B1c207E495f687a596C168E12 to {approval_amount}',  # noqa: E501
        address=string_to_evm_address('0xf5b509bB0909a69B1c207E495f687a596C168E12'),
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=2,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:137/erc20:0xeB51D9A39AD5EEF215dC0Bf39a8821ff804A0F01'),
        amount=FVal(spend_amount := '6'),
        location_label=user_address,
        notes=f'Swap {spend_amount} LGNS in quickswap-v3',
        counterparty=CPT_QUICKSWAP_V3,
        address=string_to_evm_address('0xB135Aa990D02E0a31cE953Af2bD7ed0EF6587403'),
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=3,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:137/erc20:0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063'),
        amount=FVal(receive_amount := '60.81850271428595855'),
        location_label=user_address,
        notes=f'Receive {receive_amount} DAI as the result of a swap in quickswap-v3',
        counterparty=CPT_QUICKSWAP_V3,
        address=string_to_evm_address('0xB135Aa990D02E0a31cE953Af2bD7ed0EF6587403'),
    )]
