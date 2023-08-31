import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.zksync.constants import CPT_ZKSYNC, ZKSYNC_BRIDGE
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x7277F7849966426d345D8F6B9AFD1d3d89183083']])
def test_zksync_lite_legacy_deposit(database, ethereum_inquirer, ethereum_accounts):
    """
    Test a transaction with the OnChainDeposit event which is missing
    from the newest implementation of the proxy address
    """
    tx_hex = deserialize_evm_tx_hash('0x6740ba7d674c285ce315b97dffdbf2cf91f74a2b75fba6fd82b3e0e5c8057218')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    timestamp = TimestampMS(1607624823000)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    gas_str = '0.003633546'
    dai_str = '9.4361'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=270,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            balance=Balance(amount=FVal(dai_str)),
            location_label=user_address,
            notes=f'Deposit {dai_str} DAI to zksync',
            counterparty=CPT_ZKSYNC,
            address=ZKSYNC_BRIDGE,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x7277F7849966426d345D8F6B9AFD1d3d89183083']])
def test_zksync_lite_deposit(database, ethereum_inquirer, ethereum_accounts):
    """Test a transaction with the Deposit event"""
    tx_hex = deserialize_evm_tx_hash('0x041514c879ae6f4f36c44000270ce482798502be230865911d1013978f4bcb87')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    timestamp = TimestampMS(1639578202000)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    gas_str = '0.007252433740671543'
    dai_str = '18.4614'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=139,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            balance=Balance(amount=FVal(dai_str)),
            location_label=user_address,
            notes=f'Deposit {dai_str} DAI to zksync',
            counterparty=CPT_ZKSYNC,
            address=ZKSYNC_BRIDGE,
        ),
    ]
    assert expected_events == events
