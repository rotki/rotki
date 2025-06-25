import pytest

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS, CPT_SDAI
from rotkehlchen.chain.gnosis.modules.sdai.constants import GNOSIS_SDAI_ADDRESS
from rotkehlchen.constants.assets import A_WXDAI, A_XDAI
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, Location, TimestampMS, TokenKind, deserialize_evm_tx_hash

A_GNOSIS_SDAI = evm_address_to_identifier(
    address=GNOSIS_SDAI_ADDRESS,
    chain_id=ChainID.GNOSIS,
    token_type=TokenKind.ERC20,
)


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0x78E87757861185Ec5e8C0EF6BF0C69Fa7832df6C']])
def test_deposit_xdai_to_sdai(gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0x1342646cab122d58f0b7dfae404dad5235d42224de881099dc05e59477bb93aa')  # noqa: E501
    actual_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1707169525000)
    gas_amount, deposit_amount, receive_amount = '0.000367251244452481', '315', '303.052244055946806232'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_XDAI,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} XDAI into the Savings xDAI contract',
            tx_hash=tx_hash,
            counterparty=CPT_SDAI,
            address='0xD499b51fcFc66bd31248ef4b28d656d67E591A94',
        ), EvmEvent(
            sequence_index=3020,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_GNOSIS_SDAI,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Withdraw {receive_amount} sDAI from the Savings xDAI contract',
            tx_hash=tx_hash,
            address=ZERO_ADDRESS,
            counterparty=CPT_SDAI,
        ),
    ]

    assert actual_events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0x4fFAD6ac852c0Af0AA301376F4C5Dea3a928b120']])
def test_withdraw_xdai_from_sdai(gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    receive_address = '0xD499b51fcFc66bd31248ef4b28d656d67E591A94'
    tx_hash = deserialize_evm_tx_hash('0xe23ee1ac52b8981723c737b01781691b965c5819cccccdb98e7c8cb5894dddbb')  # noqa: E501
    actual_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1707070975000)
    gas_amount, received_amount, sent_amount = '0.0003018867380459', '36546.085557613238621948', '35168.419304792460265156'  # noqa: E501

    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_XDAI,
            amount=FVal(received_amount),
            location_label=user_address,
            notes=f'Withdraw {received_amount} XDAI from the Savings xDAI contract',
            tx_hash=tx_hash,
            address=receive_address,
            counterparty=CPT_SDAI,
        ), EvmEvent(
            sequence_index=1029,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_GNOSIS_SDAI,
            amount=FVal(sent_amount),
            location_label=user_address,
            notes=f'Return {sent_amount} sDAI to the Savings xDAI contract',
            counterparty=CPT_SDAI,
            tx_hash=tx_hash,
            address=ZERO_ADDRESS,
        ),
    ]

    assert actual_events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0x5938852FE18Ad6963322FB98D1fDDA5c24DD8a0E']])
def test_deposit_wxdai_to_sdai(gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0xd406f40ecd2538d41adb2e645c8fb6d32cec5485510798bfed5d991c258d4b1d')  # noqa: E501
    actual_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1706794335000)
    withdraw_amount, deposit_amount, gas_amount = '319.006747127200240848', '331.313258668881367296', '0.0006162151'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1267,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WXDAI,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} WXDAI into the Savings xDAI contract',
            tx_hash=tx_hash,
            counterparty=CPT_SDAI,
            address='0xD499b51fcFc66bd31248ef4b28d656d67E591A94',
        ), EvmEvent(
            sequence_index=1269,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_GNOSIS_SDAI,
            amount=FVal(withdraw_amount),
            location_label=user_address,
            notes=f'Withdraw {withdraw_amount} sDAI from the Savings xDAI contract',
            tx_hash=tx_hash,
            counterparty=CPT_SDAI,
            address=ZERO_ADDRESS,
        ),
    ]

    assert actual_events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0x23727b54163F63CffdD8B7769e0eCb13Df253b4e']])
def test_withdraw_wxdai_from_sdai(gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0xd7e2123adc6c8f4fd8ced74733010cf47dba2bd4e0e5c468d63d53942b9e2dd3')  # noqa: E501
    actual_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1706699405000)
    gas_amount, redeem_amount, received_amount = '0.0002100203', '66725.257159368617313463', '69285.250334740811647229'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=373,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_GNOSIS_SDAI,
            amount=FVal(redeem_amount),
            location_label=user_address,
            notes=f'Return {redeem_amount} sDAI to the Savings xDAI contract',
            tx_hash=tx_hash,
            address=ZERO_ADDRESS,
            counterparty=CPT_SDAI,
        ), EvmEvent(
            sequence_index=374,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WXDAI,
            amount=FVal(received_amount),
            location_label=user_address,
            notes=f'Withdraw {received_amount} WXDAI from the Savings xDAI contract',
            tx_hash=tx_hash,
            address=GNOSIS_SDAI_ADDRESS,
            counterparty=CPT_SDAI,
        ),
    ]

    assert actual_events == expected_events
