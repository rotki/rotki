from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.lifi.constants import CPT_LIFI, MAYAN_SWIFT
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_MON
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

USDT0_MONAD = Asset('eip155:143/erc20:0xe7cd86e13AC4309349F30B3435a9d337750fC82D')
USDC_ETHEREUM = Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
USDC_BASE = Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
USDC_ARBITRUM = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x58ea4953f07A23232Ff6FdFcE008BBfE010f801c']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_lifi_swap_and_bridge_to_bsc(arbitrum_one_inquirer, arbitrum_one_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0x812c09ea25ccfa9db288c40d086bbec21ab23b8ebce18a9d388111488f7db945',
        )),
    )
    router = string_to_evm_address('0x89c6340B1a1f4b25D36cd8B063D49045caF3f818')
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1758745718000),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.00000564139'),
        location_label=arbitrum_one_accounts[0],
        notes='Burn 0.00000564139 ETH for gas',
        counterparty='gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(1758745718000),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal('0.000071721004734066'),
        location_label=arbitrum_one_accounts[0],
        notes='Send 0.000071721004734066 ETH to 0x89c6340B1a1f4b25D36cd8B063D49045caF3f818',
        address=router,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=TimestampMS(1758745718000),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=USDC_ARBITRUM,
        amount=FVal('57.000421'),
        location_label=arbitrum_one_accounts[0],
        notes=(
            'Set USDC spending approval of 0x58ea4953f07A23232Ff6FdFcE008BBfE010f801c '
            'by 0x89c6340B1a1f4b25D36cd8B063D49045caF3f818 to 57.000421'
        ),
        address=router,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=TimestampMS(1758745718000),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=USDC_ARBITRUM,
        amount=FVal('57.000421'),
        location_label=arbitrum_one_accounts[0],
        notes='Bridge 57.000421 USDC from Arbitrum One to Binance Smart Chain via LI.FI',
        counterparty=CPT_LIFI,
        address=router,
        extra_data={'bridge': {
            'from_chain': 42161,
            'to_chain': 56,
            'from_address': arbitrum_one_accounts[0],
            'to_address': arbitrum_one_accounts[0],
            'to_asset': '0x0000000000000000000000000000000000000000',
            'transfer_id': '9e92183abb12dfbb36fd2f8899d5531adf84398757d27988efb99c985884d945',
        }},
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('monad_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_lifi_bridge_out(monad_inquirer, monad_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=monad_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0xfc4d75dde3fe859f3ab1fc9b152a88f1f731ec1c03e3d58bc0193f5858015c87',
        )),
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1783928714000),
        location=Location.MONAD,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_MON,
        amount=FVal('0.214768446'),
        location_label=monad_accounts[0],
        notes='Burn 0.214768446 MON for gas',
        counterparty='gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(1783928714000),
        location=Location.MONAD,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_MON,
        amount=FVal('28.415576619429067927'),
        location_label=monad_accounts[0],
        notes='Spend 28.415576619429067927 MON as a LI.FI bridge fee',
        counterparty=CPT_LIFI,
        address=string_to_evm_address('0x3c6B2E0b7421254846C53c118e24c65d59eAe75e'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=38,
        timestamp=TimestampMS(1783928714000),
        location=Location.MONAD,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=USDT0_MONAD,
        amount=FVal('334.884416'),
        location_label=monad_accounts[0],
        notes='Bridge 334.884416 USDT0 from Monad to Ethereum via LI.FI',
        counterparty=CPT_LIFI,
        address=string_to_evm_address('0x3c6B2E0b7421254846C53c118e24c65d59eAe75e'),
        extra_data={'bridge': {
            'from_chain': 143,
            'to_chain': 1,
            'from_address': monad_accounts[0],
            'to_address': monad_accounts[0],
            'to_asset': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
            'transfer_id': '7ae3f916a9df3f226d02db3c9bebc60e94d4215f38b10dcb71874f1f90a79aef',
        }},
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=39,
        timestamp=TimestampMS(1783928714000),
        location=Location.MONAD,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=USDT0_MONAD,
        amount=FVal('0'),
        location_label=monad_accounts[0],
        notes=(
            'Revoke USDT0 spending approval of 0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF '
            'by 0x000000000022D473030F116dDEE9F6B43aC78BA3'
        ),
        address=string_to_evm_address('0x000000000022D473030F116dDEE9F6B43aC78BA3'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xBDaB13eb71AaA83E6917A4E7a29C00b9490DefC5']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_lifi_bridge_receive(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0xa49f28927436d0da2dae6fd07bb1d9de48436f876a57b5a4f48c4153f44be076',
        )),
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1778288423000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal('0.132711594616647501'),
        location_label=ethereum_accounts[0],
        notes='Receive 0.132711594616647501 ETH from 0xd9B2Da9C45b118e4e93A004FB1452bCDB6cC0E88',
        address=string_to_evm_address('0xd9B2Da9C45b118e4e93A004FB1452bCDB6cC0E88'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=822,
        timestamp=TimestampMS(1778288423000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=USDC_ETHEREUM,
        amount=FVal('1.541486'),
        location_label=ethereum_accounts[0],
        notes=(
            'Bridge 1.541486 USDC to 0xBDaB13eb71AaA83E6917A4E7a29C00b9490DefC5 '
            'at Ethereum via LI.FI'
        ),
        counterparty=CPT_LIFI,
        extra_data={'bridge': {
            'to_chain': 1,
            'to_address': ethereum_accounts[0],
            'transfer_id': '56697f2e5330cca44a674feb4d9c6fd45d3bd78878a0bb205c252ad30047d4ca',
        }},
        address=string_to_evm_address('0xd9B2Da9C45b118e4e93A004FB1452bCDB6cC0E88'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_lifi_intent_refund(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0xe3bf559268ec5c8e365945d28825c504e0a86d67e363274c2a6ee8509d25a4bb',
    )
    with patch(
        'rotkehlchen.chain.evm.transactions.'
        'EvmTransactions._query_and_save_internal_transactions_for_parent_hash',
        return_value=[],
    ):
        events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=54,
        timestamp=TimestampMS(1783068913000),
        location=Location.BASE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REFUND,
        asset=USDC_BASE,
        amount=FVal('128.100034'),
        location_label=base_accounts[0],
        notes='Receive 128.100034 USDC as refund from LI.FI',
        counterparty=CPT_LIFI,
        address=string_to_evm_address('0xfF0c15e93D4967554334aA54273c4799f23890c9'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x3163Bb273E8D9960Ce003fD542bF26b4C529f515']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_lifi_mayan_refund(optimism_inquirer, optimism_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0xef91ac798574eed98851b9875d77e5e5731dd5f77a69ce29e945e1177ba0847c',
        )),
    )
    expected_event = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1774211549000),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REFUND,
        asset=A_ETH,
        amount=FVal('0.01669482'),
        location_label=optimism_accounts[0],
        notes='Receive 0.01669482 ETH as refund from LI.FI',
        counterparty=CPT_LIFI,
        address=events[0].address,
    )
    assert events == [expected_event]
    assert events[0].address == MAYAN_SWIFT


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_lifi_arbitrum_native_value_is_not_a_fee(arbitrum_one_inquirer, arbitrum_one_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(
            '0x9f0a724426cc0ffbe362e9104fd52aad3e7d8097d9c2a07cbeaa9be701160af6',
        )),
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1779436285000),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000022322323572'),
        location_label=arbitrum_one_accounts[0],
        notes='Burn 0.000022322323572 ETH for gas',
        counterparty='gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(1779436285000),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal('0.327600637606583949'),
        location_label=arbitrum_one_accounts[0],
        notes='Send 0.327600637606583949 ETH to 0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE',
        address=string_to_evm_address('0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE'),
    )]
