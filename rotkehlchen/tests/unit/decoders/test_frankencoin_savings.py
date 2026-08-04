from unittest.mock import MagicMock

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.frankencoin.constants import CPT_FRANKENCOIN, ZCHF_ADDRESS
from rotkehlchen.chain.evm.decoding.frankencoin.savings.constants import (
    SAVED_TOPIC,
    SAVINGS_CONTRACT_ADDRESS,
    WITHDRAWN_TOPIC,
)
from rotkehlchen.chain.evm.decoding.frankencoin.savings.decoder import (
    FrankencoinSavingsCommonDecoder,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, Location, TimestampMS, deserialize_evm_tx_hash


def _make_savings_decoder(*, tracked: bool) -> FrankencoinSavingsCommonDecoder:
    decoder = object.__new__(FrankencoinSavingsCommonDecoder)
    decoder.base = MagicMock()
    decoder.base.is_tracked.return_value = tracked
    decoder.savings = SAVINGS_CONTRACT_ADDRESS[ChainID.ETHEREUM]
    decoder.zchf = MagicMock(
        decimals=18,
        evm_address=ZCHF_ADDRESS[ChainID.ETHEREUM],
    )
    return decoder


def _make_context(
        *,
        topic: bytes,
        decoded_events: list | None = None,
        all_logs: list[EvmTxReceiptLog] | None = None,
) -> DecoderContext:
    tx_log = EvmTxReceiptLog(
        log_index=1,
        data=(10**18).to_bytes(32),
        address=SAVINGS_CONTRACT_ADDRESS[ChainID.ETHEREUM],
        topics=[topic, bytes.fromhex('00' * 12 + '11' * 20)],
    )
    return DecoderContext(
        tx_log=tx_log,
        transaction=MagicMock(),
        action_items=[],
        all_logs=[tx_log] if all_logs is None else all_logs,
        decoded_events=[] if decoded_events is None else decoded_events,
    )


def test_savings_event_ignores_unknown_topic():
    decoder = _make_savings_decoder(tracked=True)
    context = _make_context(topic=b'\x00' * 32)

    assert decoder._decode_savings_event(context) == DEFAULT_EVM_DECODING_OUTPUT
    assert context.decoded_events == []
    decoder.base.is_tracked.assert_not_called()


def test_savings_event_ignores_untracked_owner():
    decoder = _make_savings_decoder(tracked=False)
    context = _make_context(topic=SAVED_TOPIC)

    assert decoder._decode_savings_event(context) == DEFAULT_EVM_DECODING_OUTPUT
    assert context.decoded_events == []
    decoder.base.make_event_from_transaction.assert_not_called()


def test_savings_event_handles_log_missing_from_receipt():
    decoder = _make_savings_decoder(tracked=True)
    context = _make_context(topic=SAVED_TOPIC, all_logs=[])
    decoder.base.make_event_from_transaction.return_value = expected_event = MagicMock()

    assert decoder._decode_savings_event(context) == DEFAULT_EVM_DECODING_OUTPUT
    assert context.decoded_events == [expected_event]
    assert decoder.base.make_event_from_transaction.call_args.kwargs['extra_data'] is None


def test_savings_event_handles_invalid_preceding_log():
    decoder = _make_savings_decoder(tracked=True)
    context = _make_context(topic=WITHDRAWN_TOPIC)
    context.all_logs.insert(0, EvmTxReceiptLog(
        log_index=0,
        data=b'',
        address=ZCHF_ADDRESS[ChainID.ETHEREUM],
        topics=[b'\x00' * 32, b'\x00' * 32],
    ))
    decoder.base.make_event_from_transaction.return_value = expected_event = MagicMock()

    assert decoder._decode_savings_event(context) == DEFAULT_EVM_DECODING_OUTPUT
    assert context.decoded_events == [expected_event]
    assert decoder.base.make_event_from_transaction.call_args.kwargs == {
        'transaction': context.transaction,
        'tx_log': context.tx_log,
        'event_type': HistoryEventType.WITHDRAWAL,
        'event_subtype': HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
        'asset': decoder.zchf,
        'amount': FVal(1),
        'location_label': '0x1111111111111111111111111111111111111111',
        'notes': 'Withdraw 1 zCHF from Frankencoin Savings Module',
        'counterparty': CPT_FRANKENCOIN,
        'address': decoder.savings,
        'extra_data': None,
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xbC6668371b69FD94110a9E24dCCe517CaFA2B2d1']])
def test_self_funded_deposit(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xe7e484ae4bf7b2a310eb0e6b34bc3e889940fcb85b4bd074ecf8a24a1fa5af70')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1785822875000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000013852978181768'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=209,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=(zchf := Asset(f'eip155:1/erc20:{ZCHF_ADDRESS[ChainID.ETHEREUM]}')),
            amount=FVal(interest_amount := '0.154751723536397975'),
            location_label=user_address,
            notes=f'Received {interest_amount} zCHF as interests in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=(savings_address := SAVINGS_CONTRACT_ADDRESS[ChainID.ETHEREUM]),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=210,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=zchf,
            amount=FVal(deposit_amount := '233.1475'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} zCHF in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=savings_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x84af69b785f244DC65b2D34DeE19C76EC2D519Ac']])
def test_deposit_for_another_owner(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x5ea3f06f762363b50107d73c4c785e743386f16df63111a38dd2edadd6c78237')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=804,
        timestamp=TimestampMS(1749806903000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
        asset=Asset(f'eip155:1/erc20:{ZCHF_ADDRESS[ChainID.ETHEREUM]}'),
        amount=FVal(deposit_amount := '4011.94983856871879408'),
        location_label=ethereum_accounts[0],
        notes=f'Deposit {deposit_amount} zCHF in Frankencoin Savings Module paid by '
              f'{(payer_address := "0xef91ECd0142aE4C5163B2CF060c0563d49188C82")}',
        counterparty=CPT_FRANKENCOIN,
        address=SAVINGS_CONTRACT_ADDRESS[ChainID.ETHEREUM],
        extra_data={'payer': payer_address},
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xec00b6Fd14Bac65f04623477e94D384aBeE740D6']])
def test_withdrawal_to_owner(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x3ba56721b6d1f1e6de5e5ab120625c7c78cbb73a35fcafaba05a4aaeb2db8ad2')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1785808715000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000015188280202674'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=35,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=(zchf := Asset(f'eip155:1/erc20:{ZCHF_ADDRESS[ChainID.ETHEREUM]}')),
            amount=FVal(interest_amount := '6.111720227830287294'),
            location_label=user_address,
            notes=f'Received {interest_amount} zCHF as interests in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=(savings_address := SAVINGS_CONTRACT_ADDRESS[ChainID.ETHEREUM]),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=36,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=zchf,
            amount=FVal(withdrawal_amount := '0.000031442530695338'),
            location_label=user_address,
            notes=f'Withdraw {withdrawal_amount} zCHF from Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=savings_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x772836982736cFA684c0dF6025c0A68F56bE6EDf']])
def test_withdrawal_to_another_address(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x156fd171d50187e2b53f3123e59d0d3c42b4b740e99ab1f0b1586d151f96ddf0')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1777652423000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.00016489225696348'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=652,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=Asset(f'eip155:1/erc20:{ZCHF_ADDRESS[ChainID.ETHEREUM]}'),
            amount=FVal(withdrawal_amount := '10.18221443981002012'),
            location_label=user_address,
            notes=f'Withdraw {withdrawal_amount} zCHF from Frankencoin Savings Module sent to '
                  f'{(receiver_address := "0x841FcB6309bD7BDE43890B7bE7E55E3eE86ABc39")}',
            counterparty=CPT_FRANKENCOIN,
            address=SAVINGS_CONTRACT_ADDRESS[ChainID.ETHEREUM],
            extra_data={'receiver': receiver_address},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x982dF609675D7266Ae329100FE4c955A19966c72']])
def test_interest_collection(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xba010ee7951455cebd48677e6ae9c2a65eb462df9c0b8572b3c3c5a6b82f6547')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1781423339000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.00001716401425758'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=343,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=(zchf := Asset(f'eip155:1/erc20:{ZCHF_ADDRESS[ChainID.ETHEREUM]}')),
            amount=FVal(interest_amount := '12.799257427521558132'),
            location_label=user_address,
            notes=f'Received {interest_amount} zCHF as interests in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=(savings_address := SAVINGS_CONTRACT_ADDRESS[ChainID.ETHEREUM]),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=344,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=zchf,
            amount=FVal(deposit_amount := '1797.322805687710429906'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} zCHF in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=savings_address,
        ),
    ]
