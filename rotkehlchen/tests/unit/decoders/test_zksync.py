import pytest

from rotkehlchen.chain.ethereum.modules.zksync.constants import CPT_ZKSYNC, ZKSYNC_BRIDGE
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC, A_USDT, Asset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x7277F7849966426d345D8F6B9AFD1d3d89183083']])
def test_zksync_lite_legacy_deposit(ethereum_inquirer, ethereum_accounts):
    """
    Test a transaction with the OnChainDeposit event which is missing
    from the newest implementation of the proxy address
    """
    tx_hash = deserialize_evm_tx_hash('0x6740ba7d674c285ce315b97dffdbf2cf91f74a2b75fba6fd82b3e0e5c8057218')  # noqa: E501
    timestamp = TimestampMS(1607624823000)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas_str = '0.003633546'
    dai_str = '9.4361'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=270,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            amount=FVal(dai_str),
            location_label=user_address,
            notes=f'Deposit {dai_str} DAI to zksync',
            counterparty=CPT_ZKSYNC,
            address=ZKSYNC_BRIDGE,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x7277F7849966426d345D8F6B9AFD1d3d89183083']])
def test_zksync_lite_deposit(ethereum_inquirer, ethereum_accounts):
    """Test a transaction with the Deposit event"""
    tx_hash = deserialize_evm_tx_hash('0x041514c879ae6f4f36c44000270ce482798502be230865911d1013978f4bcb87')  # noqa: E501
    timestamp = TimestampMS(1639578202000)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas_str = '0.007252433740671543'
    dai_str = '18.4614'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=139,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            amount=FVal(dai_str),
            location_label=user_address,
            notes=f'Deposit {dai_str} DAI to zksync',
            counterparty=CPT_ZKSYNC,
            address=ZKSYNC_BRIDGE,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_zksync_lite_withdrawal(ethereum_inquirer, ethereum_accounts):
    """Test a transaction with the Withdrawal event"""
    tx_hash = deserialize_evm_tx_hash('0x234407968b9a688be3fb37cf7ff8ef3b4168d6cd85ec45b8344bb2a88832f982')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, eth_str, dai_str, pan_str, usdc_str, usdt_str = TimestampMS(1604326368000), '1.4437093', '1691.92749999', '1586.6', '57.25', '15.2'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(eth_str),
            location_label=user_address,
            notes=f'Withdraw {eth_str} ETH from zksync',
            counterparty=CPT_ZKSYNC,
            address=ZKSYNC_BRIDGE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=176,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            amount=FVal(dai_str),
            location_label=user_address,
            notes=f'Withdraw {dai_str} DAI from zksync',
            counterparty=CPT_ZKSYNC,
            address=ZKSYNC_BRIDGE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=177,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0xD56daC73A4d6766464b38ec6D91eB45Ce7457c44'),
            amount=FVal(pan_str),
            location_label=user_address,
            notes=f'Withdraw {pan_str} PAN from zksync',
            counterparty=CPT_ZKSYNC,
            address=ZKSYNC_BRIDGE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=178,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDC,
            amount=FVal(usdc_str),
            location_label=user_address,
            notes=f'Withdraw {usdc_str} USDC from zksync',
            counterparty=CPT_ZKSYNC,
            address=ZKSYNC_BRIDGE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=179,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDT,
            amount=FVal(usdt_str),
            location_label=user_address,
            notes=f'Withdraw {usdt_str} USDT from zksync',
            counterparty=CPT_ZKSYNC,
            address=ZKSYNC_BRIDGE,
        ),
    ]
    assert expected_events == events
