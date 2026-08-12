from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.frankencoin.constants import (
    CPT_FRANKENCOIN,
    FRANKENCOIN_COUNTERPARTY_DETAILS,
    ZCHF_ADDRESS,
)
from rotkehlchen.chain.evm.decoding.frankencoin.savings.constants import (
    INTEREST_COLLECTED_TOPIC,
    SAVED_TOPIC,
    SUPPORTED_ZCHF_SAVINGS_CHAINS,
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
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants.assets import A_ETH, A_POL, A_XDAI
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.base import BASE_MAINNET_NODE
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.optimism import OPTIMISM_MAINNET_NODE
from rotkehlchen.types import (
    ChainID,
    Location,
    SupportedBlockchain,
    TimestampMS,
    deserialize_evm_tx_hash,
)


def _make_savings_decoder(*, tracked: bool) -> FrankencoinSavingsCommonDecoder:
    decoder = object.__new__(FrankencoinSavingsCommonDecoder)
    decoder.base = MagicMock()
    decoder.base.is_tracked.return_value = tracked
    decoder.savings_address = SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.ETHEREUM]
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
        address=SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.ETHEREUM],
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


def test_savings_event_ignores_log_without_topics():
    decoder = _make_savings_decoder(tracked=True)
    context = _make_context(topic=SAVED_TOPIC)
    context.tx_log.topics = []

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
        'address': decoder.savings_address,
        'extra_data': None,
    }


@pytest.mark.parametrize(('topic', 'initial_type', 'expected_type', 'expected_subtype', 'party_key', 'notes_connector'), [  # noqa: E501
    (SAVED_TOPIC, HistoryEventType.SPEND, HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL, 'payer', 'by'),  # noqa: E501
    (WITHDRAWN_TOPIC, HistoryEventType.RECEIVE, HistoryEventType.WITHDRAWAL, HistoryEventSubType.WITHDRAW_FROM_PROTOCOL, 'receiver', 'to'),  # noqa: E501
])
def test_savings_event_attributes_existing_transfer_to_owner(
        topic,
        initial_type,
        expected_type,
        expected_subtype,
        party_key,
        notes_connector,
):
    decoder = _make_savings_decoder(tracked=True)
    event = MagicMock(
        event_type=initial_type,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal(1),
        address=decoder.savings_address,
        asset=decoder.zchf,
        location_label=(party_address := make_evm_address()),
    )
    context = _make_context(topic=topic, decoded_events=[event])

    assert decoder._decode_savings_event(context) == DEFAULT_EVM_DECODING_OUTPUT
    assert event.event_type == expected_type
    assert event.event_subtype == expected_subtype
    assert event.counterparty == CPT_FRANKENCOIN
    assert event.location_label == '0x1111111111111111111111111111111111111111'
    assert event.extra_data == {party_key: party_address}
    assert f'{notes_connector} {party_address}' in event.notes


def test_savings_event_rejects_unrelated_preceding_transfer():
    decoder = _make_savings_decoder(tracked=True)
    context = _make_context(topic=SAVED_TOPIC)
    context.all_logs.insert(0, EvmTxReceiptLog(
        log_index=0,
        data=(10**18).to_bytes(32),
        address=make_evm_address(),
        topics=[
            ERC20_OR_ERC721_TRANSFER,
            bytes.fromhex('00' * 12 + '22' * 20),
            bytes.fromhex('00' * 12 + decoder.savings_address[2:]),
        ],
    ))
    decoder.base.make_event_from_transaction.return_value = expected_event = MagicMock()

    assert decoder._decode_savings_event(context) == DEFAULT_EVM_DECODING_OUTPUT
    assert context.decoded_events == [expected_event]
    assert decoder.base.make_event_from_transaction.call_args.kwargs['extra_data'] is None


def test_interest_collection_subtracts_referral_fee():
    decoder = _make_savings_decoder(tracked=True)
    context = _make_context(topic=INTEREST_COLLECTED_TOPIC)
    context.tx_log.data = (2 * 10**18).to_bytes(32) + (5 * 10**17).to_bytes(32)
    decoder.base.make_event_from_transaction.return_value = expected_event = MagicMock()

    assert decoder._decode_savings_event(context) == DEFAULT_EVM_DECODING_OUTPUT
    assert context.decoded_events == [expected_event]
    assert decoder.base.make_event_from_transaction.call_args.kwargs == {
        'transaction': context.transaction,
        'tx_log': context.tx_log,
        'event_type': HistoryEventType.RECEIVE,
        'event_subtype': HistoryEventSubType.INTEREST,
        'asset': decoder.zchf,
        'amount': FVal('1.5'),
        'location_label': '0x1111111111111111111111111111111111111111',
        'notes': 'Received 1.5 zCHF as interests in Frankencoin Savings Module',
        'counterparty': CPT_FRANKENCOIN,
        'address': decoder.savings_address,
    }


def test_savings_decoder_metadata():
    decoder = _make_savings_decoder(tracked=True)

    assert decoder.counterparties() == (FRANKENCOIN_COUNTERPARTY_DETAILS,)
    assert decoder.addresses_to_decoders() == {
        decoder.savings_address: (decoder._decode_savings_event,),
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
            address=(savings_address := SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.ETHEREUM]),
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
        address=SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.ETHEREUM],
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
            address=(savings_address := SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.ETHEREUM]),
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
            address=SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.ETHEREUM],
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
            address=(savings_address := SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.ETHEREUM]),
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xEf5ec96BB5761853682Ac486842f59aB7E663552']])
def test_deposit_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xa5e84fbb22e1273b842319a089e7574363d16b06a70dc6666543c119e8b28630')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1768655289000)),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000001778793984'),
            location_label=(user_address := arbitrum_one_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=Asset(f'eip155:42161/erc20:{ZCHF_ADDRESS[ChainID.ARBITRUM_ONE]}'),
            amount=FVal(deposit_amount := '1701.360556746607878987'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} zCHF in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.ARBITRUM_ONE],
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(BASE_MAINNET_NODE,)])
@pytest.mark.parametrize('base_accounts', [['0xAAafdC589d2222cE3b794876c768Eb540230aB11']])
def test_deposit_base(base_inquirer, base_accounts):
    with patch(
        'rotkehlchen.chain.evm.transactions.EvmTransactions._query_and_save_internal_transactions_for_parent_hash',
    ):
        events, _ = get_decoded_events_of_transaction(
            evm_inquirer=base_inquirer,
            tx_hash=(tx_hash := deserialize_evm_tx_hash('0x2aa42477bb168eb4532368a94c65506420abf8ea4071d96c9355032939e89d79')),  # noqa: E501
        )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1785923517000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000000430021640992'),
            location_label=(user_address := base_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=322,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=Asset(f'eip155:8453/erc20:{ZCHF_ADDRESS[ChainID.BASE]}'),
            amount=FVal(deposit_amount := '5'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} zCHF in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.BASE],
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_manager_connect_at_start', [(OPTIMISM_MAINNET_NODE,)])
@pytest.mark.parametrize('optimism_accounts', [['0xc35A45BcF42BeE24bB62D512b8aA08660cc8a3d3']])
def test_deposit_optimism(optimism_inquirer, optimism_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xbe24c79aa348b94e116dd58cc14134acdb703ac1b5d8136113fa295ffd86d816')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1785774967000)),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000001133643733036'),
            location_label=(user_address := optimism_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=Asset(f'eip155:10/erc20:{ZCHF_ADDRESS[ChainID.OPTIMISM]}'),
            amount=FVal(deposit_amount := '1'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} zCHF in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.OPTIMISM],
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x726397F95bcE98505d67480457071896962f85AC']])
def test_deposit_polygon_pos(polygon_pos_inquirer, polygon_pos_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x439c5f7f120f8fce87c589b83211527085d04c0e093748511c5df63f5df9a245')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783018649000)),
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POL,
            amount=FVal(gas_amount := '0.050978100548580012'),
            location_label=(user_address := polygon_pos_accounts[0]),
            notes=f'Burn {gas_amount} POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1166,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=Asset(f'eip155:137/erc20:{ZCHF_ADDRESS[ChainID.POLYGON_POS]}'),
            amount=FVal(deposit_amount := '1'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} zCHF in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.POLYGON_POS],
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_manager_connect_at_start', [(WeightedNode(
    node_info=NodeName(
        name='gnosis public node',
        endpoint='https://gnosis.publicnode.com',
        owned=False,
        blockchain=SupportedBlockchain.GNOSIS,
    ),
    active=True,
    weight=ONE,
),)])
@pytest.mark.parametrize('gnosis_accounts', [['0x5D0cE9De9F4a26e3999dCE56Ff62cA5Db97608e3']])
def test_deposit_gnosis(gnosis_inquirer, gnosis_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x1bf9048db6bc58f5c3b9f34656992e39111cbef83b088eeb54b49cb09189ce82')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1785931065000)),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount := '0.0000871440130716'),
            location_label=(user_address := gnosis_accounts[0]),
            notes=f'Burn {gas_amount} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=13,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=(zchf := Asset(f'eip155:100/erc20:{ZCHF_ADDRESS[ChainID.GNOSIS]}')),
            amount=FVal(interest_amount := '32.403386488099250454'),
            location_label=user_address,
            notes=f'Received {interest_amount} zCHF as interests in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=(savings_address := SUPPORTED_ZCHF_SAVINGS_CHAINS[ChainID.GNOSIS]),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=zchf,
            amount=FVal(deposit_amount := '11279.78'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} zCHF in Frankencoin Savings Module',
            counterparty=CPT_FRANKENCOIN,
            address=savings_address,
        ),
    ]
