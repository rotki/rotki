import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.lido.constants import CPT_LIDO
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.constants.assets import A_ETH, A_STETH, A_WSTETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4C49d4Bd6a571827B4A556a0e1e3071DA6231B9D']])
def test_lido_steth_staking(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x23a3ee601475424e91bdc0999a780afe57bf37cbcce6d1c09a4dfaaae1765451')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    timestamp, gas_str, amount_deposited, amount_minted = TimestampMS(1710486191000), '0.002846110430778206', '1.12137397', '1.121373969999999999'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
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
            tx_hash=evmhash,
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
            tx_hash=evmhash,
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


# @pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4F243B4b795502AA5Cf562cB42EccD444c0321b0']])
def test_lido_wsteth_wrapping(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x21e291c980e6ca90b6b52bf13bc43c26bead4d3129bdbc463e140592294fe5bd')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    timestamp, gas_str, amount_wsteth, amount_steth = TimestampMS(1733619851000), '0.00117399752663733', '22.101307407211190709', '26.235763844022460916'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
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
            tx_hash=evmhash,
            sequence_index=323,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_STETH,
            amount=FVal(0),
            location_label=ethereum_accounts[0],
            notes='Revoke stETH spending approval of 0x4F243B4b795502AA5Cf562cB42EccD444c0321b0 by 0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0',  # noqa: E501
            counterparty=None,
            address=A_WSTETH.resolve_to_evm_token().evm_address,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=324,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_STETH,
            amount=FVal(amount_steth),
            location_label=ethereum_accounts[0],
            notes=f'Wrap {amount_steth} {A_STETH.symbol_or_name()} in {A_WSTETH.symbol_or_name()}',
            counterparty=CPT_LIDO,
            address=A_STETH.resolve_to_evm_token().evm_address,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=325,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WSTETH,
            amount=FVal(amount_wsteth),
            location_label=ethereum_accounts[0],
            notes=f'Receive {amount_wsteth} wstETH',
            counterparty=CPT_LIDO,
            address=A_WSTETH.resolve_to_evm_token().evm_address,
        ),

    ]
    assert events == expected_events


# @pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x29eC7360170367F86F4e18dA8Cf232A9C108Dc60']])
def test_lido_wsteth_unwrapping(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x104e9b227fb672dd32f3b9bfca002eec783846a6e8787010f6c0f5579f111ef1')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    timestamp, gas_str, amount_wsteth, amount_steth = TimestampMS(1759185275000), '0.000030746884486906', '22.593785199529477044', '27.451978417858478677'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
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
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WSTETH,
            amount=FVal(amount_wsteth),
            location_label=ethereum_accounts[0],
            notes=f'Unwrap {amount_wsteth} {A_WSTETH.symbol_or_name()}',
            counterparty=CPT_LIDO,
            address=A_WSTETH.resolve_to_evm_token().evm_address,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_STETH,
            amount=FVal(amount_steth),
            location_label=ethereum_accounts[0],
            notes=f'Receive {amount_steth} stETH',
            counterparty=CPT_LIDO,
            address=A_STETH.resolve_to_evm_token().evm_address,
        ),

    ]
    assert events == expected_events
