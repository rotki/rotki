import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BEETS_V3
from rotkehlchen.constants.assets import A_S
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.sonic import SONIC_MAINNET_NODE
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

SONIC_JOIN_TX = '0x7a9c32f90fa234cd657c5203d4fb82d0f0f7697a610536d60e9a4e89932b1ad6'
SONIC_EXIT_TX = '0xe9de55d23662c884d1af17cea9d1ba5893398bc031b8000dc8e7f00c13d9cc83'

BW_S25 = 'eip155:146/erc20:0x016C306e103FbF48EC24810D078C65aD13c5f11B'
AN_S = 'eip155:146/erc20:0x0C4E186Eae8aCAA7F7de1315D5AD174BE39Ec987'
AN_S_SILO_WS = 'eip155:146/erc20:0x944D4AE892dE4BFd38742Cc8295d6D5164c5593C'
SONIC_VAULT = '0xbA1333333333a1BA1108E8412f11850A5C319bA9'


@pytest.mark.parametrize('sonic_manager_connect_at_start', [(SONIC_MAINNET_NODE,)])
@pytest.mark.parametrize('sonic_accounts', [['0xaBf0f7bD0Dc8Ce44b084B4B66b8Db97F1b9Ce419']])
def test_beets_v3_join(sonic_inquirer, sonic_accounts):
    """A Beets v3 pool join through the BatchRouter."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=sonic_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(SONIC_JOIN_TX)),
    )
    user = sonic_accounts[0]
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1780911712000)),
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_S,
        amount=FVal(gas_amount := '0.021755361'),
        location_label=user,
        notes=f'Burn {gas_amount} S for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=BW_S25,
        amount=FVal(deposit_amount := '57108698.517387971172847294'),
        location_label=user,
        notes=f'Deposit {deposit_amount} bwS-25 to a Balancer v3 pool',
        counterparty=CPT_BEETS_V3,
        address=SONIC_VAULT,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=AN_S_SILO_WS,
        amount=FVal(receive_amount := '59117.322877638191625628'),
        location_label=user,
        notes=f'Receive {receive_amount} bpt-anS-SiloWS from a Balancer v3 pool',
        counterparty=CPT_BEETS_V3,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.parametrize('sonic_manager_connect_at_start', [(SONIC_MAINNET_NODE,)])
@pytest.mark.parametrize('sonic_accounts', [['0x5FadCB810A04bB94D7fFb7902E4dc67e43ef0701']])
def test_beets_v3_exit(sonic_inquirer, sonic_accounts):
    """A Beets v3 pool exit through the BatchRouter."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=sonic_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(SONIC_EXIT_TX)),
    )
    user = sonic_accounts[0]
    assert events[0] == EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1785258173000)),
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_S,
        amount=FVal(gas_amount := '0.0296091592182'),
        location_label=user,
        notes=f'Burn {gas_amount} S for gas',
        counterparty=CPT_GAS,
    )
    assert [event for event in events if event.counterparty == CPT_BEETS_V3] == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=14,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=AN_S_SILO_WS,
        amount=FVal(return_amount := '42627.56908477590344007'),
        location_label=user,
        notes=f'Return {return_amount} bpt-anS-SiloWS to a Balancer v3 pool',
        counterparty=CPT_BEETS_V3,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=15,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=AN_S,
        amount=FVal(withdraw_amount := '27686.422638507350115348'),
        location_label=user,
        notes=f'Withdraw {withdraw_amount} anS from a Balancer v3 pool',
        counterparty=CPT_BEETS_V3,
        address=SONIC_VAULT,
    )]
