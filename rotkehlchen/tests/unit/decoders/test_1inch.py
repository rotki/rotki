import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.oneinch.constants import CPT_ONEINCH_V1, CPT_ONEINCH_V2
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_CHI, A_PAN
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_1inchv1_swap(database, ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0x8b8652c502e80ce7c5441cdedc9184ea8f07a9c13b4c3446a47ae08c6c1d6efa
    """
    tx_hash = deserialize_evm_tx_hash('0x8b8652c502e80ce7c5441cdedc9184ea8f07a9c13b4c3446a47ae08c6c1d6efa')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    chispender_addy = string_to_evm_address('0xed04A060050cc289d91779A8BB3942C3A6589254')
    oneinch_contract = string_to_evm_address('0x11111254369792b2Ca5d084aB5eEA397cA8fa48B')
    timestamp = TimestampMS(1594500575000)
    expected_events = [
        EvmEvent(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00896373909')),
            location_label=ADDY,
            notes='Burned 0.00896373909 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            event_identifier=tx_hash,
            sequence_index=90,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            balance=Balance(amount=FVal('138.75')),
            location_label=ADDY,
            notes=f'Swap 138.75 USDC in {CPT_UNISWAP_V2}',
            counterparty=CPT_UNISWAP_V2,
            address=oneinch_contract,
        ), EvmEvent(
            event_identifier=tx_hash,
            sequence_index=91,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DAI,
            balance=Balance(amount=FVal('135.959878392183347402')),
            location_label=ADDY,
            notes=f'Receive 135.959878392183347402 DAI from 1inch-v1 swap in {ADDY}',
            counterparty=CPT_ONEINCH_V1,
            address=oneinch_contract,
        ), EvmEvent(
            event_identifier=tx_hash,
            sequence_index=103,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_CHI,
            balance=Balance(),
            location_label=ADDY,
            notes=f'Revoke CHI spending approval of {ADDY} by {chispender_addy}',
            address=chispender_addy,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_1inchv2_swap_for_eth(database, ethereum_inquirer):
    """
    Test an 1inchv2 swap for ETH.

    Data taken from
    https://etherscan.io/tx/0x5edc23d5a05e347afc60e64a4d5831ed2551985c21dceb85d267926ca2e2c13e
    """
    tx_hash = deserialize_evm_tx_hash('0x5edc23d5a05e347afc60e64a4d5831ed2551985c21dceb85d267926ca2e2c13e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1608498702000)
    oneinch_v2_addy = string_to_evm_address('0x111111125434b319222CdBf8C261674aDB56F3ae')
    expected_events = [
        EvmEvent(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.002618947')),
            location_label=ADDY,
            notes='Burned 0.002618947 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            event_identifier=tx_hash,
            sequence_index=217,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_PAN,
            balance=Balance(amount=FVal('2152.63')),
            location_label=ADDY,
            notes='Swap 2152.63 PAN in 1inch-v2',
            counterparty=CPT_ONEINCH_V2,
            address=string_to_evm_address('0xd47140F6Ab73f6d6B6675Fb1610Bb5E9B5d96FE5'),
        ), EvmEvent(
            event_identifier=tx_hash,
            sequence_index=218,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.220582251767407014')),
            location_label=ADDY,
            notes='Receive 0.220582251767407014 ETH from 1inch-v2 swap',
            counterparty=CPT_ONEINCH_V2,
            address=string_to_evm_address('0xF53bBFBff01c50F2D42D542b09637DcA97935fF7'),
        ), EvmEvent(
            event_identifier=tx_hash,
            sequence_index=221,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_PAN,
            balance=Balance(amount=FVal('1.157920892373161954235709850E+59')),
            location_label=ADDY,
            notes=f'Set PAN spending approval of {ADDY} by {oneinch_v2_addy} to 115792089237316195423570985000000000000000000000000000000000',  # noqa: E501
            address=oneinch_v2_addy,
        ),
    ]
    assert expected_events == events
