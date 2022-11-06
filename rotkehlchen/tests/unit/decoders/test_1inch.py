import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.constants import ZERO_ADDRESS
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.oneinch.constants import CPT_ONEINCH_V1, CPT_ONEINCH_V2
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_CHI, A_PAN
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_1inchv1_swap(database, ethereum_manager, function_scope_messages_aggregator):
    """Data taken from
    https://etherscan.io/tx/0x8b8652c502e80ce7c5441cdedc9184ea8f07a9c13b4c3446a47ae08c6c1d6efa
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0x8b8652c502e80ce7c5441cdedc9184ea8f07a9c13b4c3446a47ae08c6c1d6efa')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        tx_hash=tx_hash,
    )
    chispender_addy = '0xed04A060050cc289d91779A8BB3942C3A6589254'
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1594500575000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00896373909')),
            location_label=ADDY,
            notes='Burned 0.00896373909 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=90,
            timestamp=1594500575000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            balance=Balance(amount=FVal('138.75')),
            location_label=ADDY,
            notes=f'Swap 138.75 USDC in uniswap-v2 from {ADDY}',
            counterparty=CPT_UNISWAP_V2,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=91,
            timestamp=1594500575000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DAI,
            balance=Balance(amount=FVal('135.959878392183347402')),
            location_label=ADDY,
            notes=f'Receive 135.959878392183347402 DAI from 1inch-v1 swap in {ADDY}',
            counterparty=CPT_ONEINCH_V1,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=102,
            timestamp=1594500575000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_CHI,
            balance=Balance(),
            location_label=ADDY,
            notes=f'Send 0 CHI from {ADDY} to {ZERO_ADDRESS}',
            counterparty=ZERO_ADDRESS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=103,
            timestamp=1594500575000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_CHI,
            balance=Balance(),
            location_label=ADDY,
            notes=f'Revoke CHI approval of {ADDY} for spending by {chispender_addy}',
            counterparty=chispender_addy,
        ),
    ]
    assert expected_events == events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_1inchv2_swap_for_eth(database, ethereum_manager, function_scope_messages_aggregator):
    """
    Test an 1inchv2 swap for ETH.

    Data taken from
    https://etherscan.io/tx/0x5edc23d5a05e347afc60e64a4d5831ed2551985c21dceb85d267926ca2e2c13e
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0x5edc23d5a05e347afc60e64a4d5831ed2551985c21dceb85d267926ca2e2c13e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        tx_hash=tx_hash,
    )
    oneinch_v2_addy = '0x111111125434b319222CdBf8C261674aDB56F3ae'
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1608498702000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.002618947')),
            location_label=ADDY,
            notes='Burned 0.002618947 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=217,
            timestamp=1608498702000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_PAN,
            balance=Balance(amount=FVal('2152.63')),
            location_label=ADDY,
            notes='Swap 2152.63 PAN in 1inch-v2',
            counterparty=CPT_ONEINCH_V2,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=218,
            timestamp=1608498702000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.220582251767407014')),
            location_label=ADDY,
            notes='Receive 0.220582251767407014 ETH from 1inch-v2 swap',
            counterparty=CPT_ONEINCH_V2,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=221,
            timestamp=1608498702000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_PAN,
            balance=Balance(amount=FVal('1.157920892373161954235709850E+59')),
            location_label=ADDY,
            notes=f'Approve 1.157920892373161954235709850E+59 PAN of {ADDY} for spending by {oneinch_v2_addy}',  # noqa: E501
            counterparty=oneinch_v2_addy,
        ),
    ]
    assert expected_events == events
