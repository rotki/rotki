import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BEETS_V2, CPT_BEETS_V3
from rotkehlchen.chain.sonic.modules.wson.constants import CPT_WSON
from rotkehlchen.constants.assets import A_S, A_WS
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.sonic import SONIC_MAINNET_NODE
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

SONIC_JOIN_TX = '0x7a9c32f90fa234cd657c5203d4fb82d0f0f7697a610536d60e9a4e89932b1ad6'
SONIC_EXIT_TX = '0xe9de55d23662c884d1af17cea9d1ba5893398bc031b8000dc8e7f00c13d9cc83'
WS_ADDRESS = '0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38'

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
@pytest.mark.parametrize('sonic_accounts', [['0x801EF3Bf0883b1fDC72669C7d2f368D8c3845d6e']])
def test_beets_v3_swap(sonic_inquirer, sonic_accounts):
    """A Beets v3 single-hop swap of stS for wS."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=sonic_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x37a9d5c10758591a79d984c4fdca62612212d31efa0943bc2f6018069208dad9')),  # noqa: E501
    )
    user = sonic_accounts[0]
    pool = '0x8F10B468b06c6FD214B65F87778827F7D113f996'
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1786620723000)),
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_S,
        amount=FVal(gas_amount := '0.014681300000293626'),
        location_label=user,
        notes=f'Burn {gas_amount} S for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset='eip155:146/erc20:0xE5DA20F15420aD15DE0fa650600aFc998bbE3955',
        amount=FVal(spend_amount := '70000'),
        location_label=user,
        notes=f'Swap {spend_amount} stS in Balancer v3',
        counterparty=CPT_BEETS_V3,
        address=pool,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset='eip155:146/erc20:0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38',
        amount=FVal(receive_amount := '75338.927873086636250054'),
        location_label=user,
        notes=f'Receive {receive_amount} wS as the result of a swap in Balancer v3',
        counterparty=CPT_BEETS_V3,
        address=pool,
    )]


@pytest.mark.parametrize('sonic_manager_connect_at_start', [(SONIC_MAINNET_NODE,)])
@pytest.mark.parametrize('sonic_accounts', [['0xda20986e2D4FaeB3B4C949E9c0Ab5630D8Ac0914']])
def test_beets_v2_join(sonic_inquirer, sonic_accounts):
    """A Beets v2 pool join of three tokens directly through the vault."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=sonic_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x22f8c09f5d945aec30f4e9f60f4b7539abd547269844f89d231ebd7a90a7720d')),  # noqa: E501
    )
    user = sonic_accounts[0]
    vault = '0xBA12222222228d8Ba445958a75a0704d566BF2C8'
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1751905538000)),
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_S,
        amount=FVal(gas_amount := '0.01822623'),
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
        asset='eip155:146/erc20:0x3bcE5CB273F0F148010BbEa2470e7b5df84C7812',
        amount=FVal(sceth_amount := '0.037175112093163958'),
        location_label=user,
        notes=f'Deposit {sceth_amount} scETH to a Balancer v2 pool',
        counterparty=CPT_BEETS_V2,
        address=vault,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset='eip155:146/erc20:0xd3DCe716f3eF535C5Ff8d041c1A41C3bd89b97aE',
        amount=FVal(scusd_amount := '94.143991'),
        location_label=user,
        notes=f'Deposit {scusd_amount} scUSD to a Balancer v2 pool',
        counterparty=CPT_BEETS_V2,
        address=vault,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset='eip155:146/erc20:0xE5DA20F15420aD15DE0fa650600aFc998bbE3955',
        amount=FVal(sts_amount := '573.366037918215836679'),
        location_label=user,
        notes=f'Deposit {sts_amount} stS to a Balancer v2 pool',
        counterparty=CPT_BEETS_V2,
        address=vault,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset='eip155:146/erc20:0x32BAC522c4F97F4913d18D81Cf3bE119c8Cce26a',
        amount=FVal(pool_amount := '557231.474081683784771027'),
        location_label=user,
        notes=f'Receive {pool_amount} 10stS-10scETH-10scUSD-70F from a Balancer v2 pool',
        counterparty=CPT_BEETS_V2,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.parametrize('sonic_manager_connect_at_start', [(SONIC_MAINNET_NODE,)])
@pytest.mark.parametrize('sonic_accounts', [['0xCB6586874cc04B01Cc4fDB777dE502cEa7b3D6c1']])
def test_beets_v2_exit(sonic_inquirer, sonic_accounts):
    """A Beets v2 pool exit of four tokens directly through the vault."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=sonic_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x67dc26e6a19bb69cc49bb0d3b678d512d9dc78ba0c76f171eac748462d2fab5d')),  # noqa: E501
    )
    user = sonic_accounts[0]
    vault = '0xBA12222222228d8Ba445958a75a0704d566BF2C8'
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1778192359000)),
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_S,
        amount=FVal(gas_amount := '0.016167450000323349'),
        location_label=user,
        notes=f'Burn {gas_amount} S for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset='eip155:146/erc20:0x32BAC522c4F97F4913d18D81Cf3bE119c8Cce26a',
        amount=FVal(return_amount := '38952.503374014711216412'),
        location_label=user,
        notes=f'Return {return_amount} 10stS-10scETH-10scUSD-70F to a Balancer v2 pool',
        counterparty=CPT_BEETS_V2,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset='eip155:146/erc20:0x3bcE5CB273F0F148010BbEa2470e7b5df84C7812',
        amount=FVal(sceth_amount := '0.000430940611224193'),
        location_label=user,
        notes=f'Receive {sceth_amount} scETH after removing liquidity from a Balancer v2 pool',
        counterparty=CPT_BEETS_V2,
        address=vault,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset='eip155:146/erc20:0xBe422DD2F451348d5D0979D8ab25B4c6eAAd1eB2',
        amount=FVal(f_amount := '1125014.199838167776212026'),
        location_label=user,
        notes=f'Receive {f_amount} F after removing liquidity from a Balancer v2 pool',
        counterparty=CPT_BEETS_V2,
        address=vault,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset='eip155:146/erc20:0xd3DCe716f3eF535C5Ff8d041c1A41C3bd89b97aE',
        amount=FVal(scusd_amount := '0.991061'),
        location_label=user,
        notes=f'Receive {scusd_amount} scUSD after removing liquidity from a Balancer v2 pool',
        counterparty=CPT_BEETS_V2,
        address=vault,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset='eip155:146/erc20:0xE5DA20F15420aD15DE0fa650600aFc998bbE3955',
        amount=FVal(sts_amount := '19.123213205894685941'),
        location_label=user,
        notes=f'Receive {sts_amount} stS after removing liquidity from a Balancer v2 pool',
        counterparty=CPT_BEETS_V2,
        address=vault,
    )]


@pytest.mark.parametrize('sonic_manager_connect_at_start', [(SONIC_MAINNET_NODE,)])
@pytest.mark.parametrize('sonic_accounts', [['0x5541B7D1F2f0d5A6bA921156ce48D97f9D212e02']])
def test_wson_wrap(sonic_inquirer, sonic_accounts):
    """Wrapping S to WS."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=sonic_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x86a5bbf5779febadd088a90ed51bf3f8d5aafe607575610b9153f4f31390d5fc')),  # noqa: E501
    )
    user = sonic_accounts[0]
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1786621087000)),
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_S,
        amount=FVal(gas_amount := '0.0103176'),
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
        asset=A_S,
        amount=FVal(wrapped_amount := '12923'),
        location_label=user,
        notes=f'Wrap {wrapped_amount} S in wS',
        counterparty=CPT_WSON,
        address=WS_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_WS,
        amount=FVal(wrapped_amount),
        location_label=user,
        notes=f'Receive {wrapped_amount} wS',
        counterparty=CPT_WSON,
        address=WS_ADDRESS,
    )]


@pytest.mark.parametrize('sonic_manager_connect_at_start', [(SONIC_MAINNET_NODE,)])
@pytest.mark.parametrize('sonic_accounts', [['0xCB4fF53cfC5747611CFD2d89dA9114c243Bea3d5']])
def test_wson_unwrap(sonic_inquirer, sonic_accounts):
    """Unwrapping WS to S."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=sonic_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xfde79c92224ed64a63b0cf23e7b79739d44c0c65331d7bb0d57540bc98a30540')),  # noqa: E501
    )
    user = sonic_accounts[0]
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1786621203000)),
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_S,
        amount=FVal(gas_amount := '0.001908100000038162'),
        location_label=user,
        notes=f'Burn {gas_amount} S for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_WS,
        amount=FVal(unwrapped_amount := '538.947586765268183953'),
        location_label=user,
        notes=f'Unwrap {unwrapped_amount} wS',
        counterparty=CPT_WSON,
        address=WS_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_S,
        amount=FVal(unwrapped_amount),
        location_label=user,
        notes=f'Receive {unwrapped_amount} S',
        counterparty=CPT_WSON,
        address=WS_ADDRESS,
    )]


@pytest.mark.parametrize('sonic_manager_connect_at_start', [(SONIC_MAINNET_NODE,)])
@pytest.mark.parametrize('sonic_accounts', [['0x725AbD8eb83d0f22E905B1e60884b98c8314CB93']])
def test_beets_v2_swap(sonic_inquirer, sonic_accounts):
    """A Beets v2 single-hop swap of stS for scUSD through the vault."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=sonic_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x6c583ce6f57b6ffd0b48be4cf6083a93d9926ba5eccaaa066d74bbad3d0b1101')),  # noqa: E501
    )
    user = sonic_accounts[0]
    vault = '0xBA12222222228d8Ba445958a75a0704d566BF2C8'
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1786620857000)),
        location=Location.SONIC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_S,
        amount=FVal(gas_amount := '0.008759322'),
        location_label=user,
        notes=f'Burn {gas_amount} S for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset='eip155:146/erc20:0xE5DA20F15420aD15DE0fa650600aFc998bbE3955',
        amount=FVal(spend_amount := '230.76923'),
        location_label=user,
        notes=f'Swap {spend_amount} stS in Balancer v2',
        counterparty=CPT_BEETS_V2,
        address=vault,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.SONIC,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset='eip155:146/erc20:0xd3DCe716f3eF535C5Ff8d041c1A41C3bd89b97aE',
        amount=FVal(receive_amount := '5.643006'),
        location_label=user,
        notes=f'Receive {receive_amount} scUSD as the result of a swap in Balancer v2',
        counterparty=CPT_BEETS_V2,
        address=vault,
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
