import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.oneinch.constants import CPT_ONEINCH_V1, CPT_ONEINCH_V2
from rotkehlchen.chain.ethereum.modules.oneinch.v2.constants import ONEINCH_V2_MAINNET_ROUTER
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.oneinch.constants import CPT_ONEINCH
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.polygon_pos.modules.oneinch.constants import ONEINCH_POLYGON_POS_ROUTER
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_POLYGON_POS_MATIC, A_USDC
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
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=104,
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
            tx_hash=tx_hash,
            sequence_index=105,
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
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=218,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_PAN,
            balance=Balance(amount=FVal('1.157920892373161954235709850E+59')),
            location_label=ADDY,
            notes=f'Set PAN spending approval of {ADDY} by {ONEINCH_V2_MAINNET_ROUTER} to 115792089237316195423570985000000000000000000000000000000000',  # noqa: E501
            address=ONEINCH_V2_MAINNET_ROUTER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=219,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_PAN,
            balance=Balance(amount=FVal('2152.63')),
            location_label=ADDY,
            notes='Swap 2152.63 PAN in 1inch-v2',
            counterparty=CPT_ONEINCH_V2,
            address=ONEINCH_V2_MAINNET_ROUTER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=220,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.220582251767407014')),
            location_label=ADDY,
            notes='Receive 0.220582251767407014 ETH from 1inch-v2 swap',
            counterparty=CPT_ONEINCH_V2,
            address=ONEINCH_V2_MAINNET_ROUTER,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('polygon_pos_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_1inch_swap_polygon(database, polygon_pos_inquirer, polygon_pos_accounts):
    """Data taken from
    https://polygonscan.com/tx/0xe13e0ebab7a6abc0c0a22fcf0766b9a585a430415c88f3f90328b310119a85af
    """
    tx_hash = deserialize_evm_tx_hash('0xe13e0ebab7a6abc0c0a22fcf0766b9a585a430415c88f3f90328b310119a85af')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_addy = polygon_pos_accounts[0]
    pos_usdt = Asset('eip155:137/erc20:0xc2132D05D31c914a87C6611C10748AEb04B58e8F')
    pos_yfi = Asset('eip155:137/erc20:0xDA537104D6A5edd53c6fBba9A898708E465260b6')
    timestamp = TimestampMS(1641040985000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            balance=Balance(amount=FVal('0.0579902')),
            location_label=user_addy,
            notes='Burned 0.0579902 MATIC for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=277,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=pos_usdt,
            balance=Balance(FVal('115792089237316195423570985000000000000000000000000000000000000000000000')),
            location_label=user_addy,
            notes=f'Set USDT spending approval of {user_addy} by {ONEINCH_POLYGON_POS_ROUTER} to 115792089237316195423570985000000000000000000000000000000000000000000000',  # noqa: E501
            address=ONEINCH_POLYGON_POS_ROUTER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=278,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=pos_usdt,
            balance=Balance(amount=FVal('96.795')),
            location_label=user_addy,
            notes='Swap 96.795 USDT in 1inch',
            counterparty=CPT_ONEINCH,
            address=ONEINCH_POLYGON_POS_ROUTER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=279,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=pos_yfi,
            balance=Balance(amount=FVal('0.002830144606136162')),
            location_label=user_addy,
            notes='Receive 0.002830144606136162 YFI from 1inch swap',
            counterparty=CPT_ONEINCH,
            address=ONEINCH_POLYGON_POS_ROUTER,
        ),
    ]
    assert expected_events == events
