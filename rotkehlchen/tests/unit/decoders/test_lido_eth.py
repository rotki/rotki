import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.lido.constants import CPT_LIDO
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.constants.assets import A_ETH, A_STETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4C49d4Bd6a571827B4A556a0e1e3071DA6231B9D']])
def test_lido_steth_staking(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x23a3ee601475424e91bdc0999a780afe57bf37cbcce6d1c09a4dfaaae1765451')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_str, amount_deposited, amount_minted = TimestampMS(1710486191000), '0.002846110430778206', '1.12137397', '1.121373969999999999'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount_deposited),
            location_label=ethereum_accounts[0],
            notes=f'Submit {amount_deposited} {A_ETH.symbol_or_name()} to Lido',
            counterparty=CPT_LIDO,
            address=A_STETH.resolve_to_evm_token().evm_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_STETH,
            amount=FVal(amount_minted),
            location_label=ethereum_accounts[0],
            notes=f'Receive {amount_minted} {A_STETH.symbol_or_name()} in exchange for the deposited {A_ETH.symbol_or_name()}',  # noqa: E501
            counterparty=CPT_LIDO,
            address=ZERO_ADDRESS,
            extra_data={'staked_eth': str(amount_deposited)},
        ),
    ]
    assert events == expected_events
