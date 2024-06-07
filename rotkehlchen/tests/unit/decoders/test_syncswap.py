from typing import Final

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.scroll.modules.syncswap.decoder import (
    CPT_SYNCSWAP,
    SYNCSWAP_ROUTER_ADDRESS,
    SYNCSWAP_VAULT_ADDRESS,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, EvmTokenKind, Location, TimestampMS, deserialize_evm_tx_hash

USDC_SCROLL_EIP155: Final = 'eip155:534352/erc20:0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4'
USDT_SCROLL_EIP155: Final = 'eip155:534352/erc20:0xf55BEC9cafDbE8730f096Aa55dad6D22d44099Df'
DAI_SCROLL_EIP155: Final = 'eip155:534352/erc20:0xcA77eB3fEFe3725Dc33bccB54eDEFc3D9f764f97'


@pytest.mark.vcr()
@pytest.mark.parametrize('scroll_accounts', [['0x3D2F6f18c51F3b72382F5Aea85bDe2cFeaB25dc6']])
def test_scroll_syncswap_eth_usdc_swap(database, scroll_inquirer, scroll_accounts):
    """Swap ETH for USDC on scroll"""
    evmhash = deserialize_evm_tx_hash('0xaa2f8589fa581506c067ad128c00dfce35c98daa49d58ea9e27ad4d2bc782084')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=scroll_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    timestamp = TimestampMS(1713530626000)
    fee = FVal('0.00024694228625118')
    amount_received_usdc = FVal('36.508481')
    amount_sent_eth = FVal('0.01180498459310175')
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=fee, usd_value=ZERO),
            location_label=scroll_accounts[0],
            notes=f'Burned {fee} ETH for gas',
            counterparty='gas',
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=amount_sent_eth, usd_value=ZERO),
            location_label=scroll_accounts[0],
            notes=f'Swap {amount_sent_eth} ETH in syncswap from {scroll_accounts[0]}',
            counterparty=CPT_SYNCSWAP,
            address=SYNCSWAP_ROUTER_ADDRESS,
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken(USDC_SCROLL_EIP155),
            balance=Balance(amount=amount_received_usdc, usd_value=ZERO),
            location_label=scroll_accounts[0],
            notes=f'Receive {amount_received_usdc} USDC in syncswap from {scroll_accounts[0]}',
            counterparty=CPT_SYNCSWAP,
            address=SYNCSWAP_VAULT_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('scroll_accounts', [['0xd32dEe97C7D7Fdfb826CC3bB210dD009D2750ae2']])
def test_scroll_syncswap_usdc_dai_swap(database, scroll_inquirer, scroll_accounts):
    evmhash = deserialize_evm_tx_hash('0x21bd217a16008bd9c726dad335c0329cf500a835e2571ebb15df94b4b37e676d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=scroll_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    timestamp = TimestampMS(1713637322000)
    fee = FVal('0.000377023919934224')
    approval_amount = FVal('115792089237316195423570985008687907853269984665640564039457584007913129.639935')  # noqa: E501
    amount_sent_usdc = FVal('5')
    amount_received_dai = FVal('4.99644225248524218')
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=fee, usd_value=ZERO),
            location_label=scroll_accounts[0],
            notes=f'Burned {fee} ETH for gas',
            counterparty='gas',
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=17,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken(USDC_SCROLL_EIP155),
            balance=Balance(amount=approval_amount, usd_value=ZERO),
            location_label=scroll_accounts[0],
            notes=f'Set USDC spending approval of {scroll_accounts[0]} by {SYNCSWAP_ROUTER_ADDRESS} to {approval_amount}',  # noqa: E501
            address=SYNCSWAP_ROUTER_ADDRESS,
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=18,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=EvmToken(USDC_SCROLL_EIP155),
            balance=Balance(amount=amount_sent_usdc, usd_value=ZERO),
            location_label=scroll_accounts[0],
            notes=f'Swap {amount_sent_usdc} USDC in syncswap from {scroll_accounts[0]}',
            counterparty=CPT_SYNCSWAP,
            address=SYNCSWAP_VAULT_ADDRESS,
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=19,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken(DAI_SCROLL_EIP155),
            balance=Balance(amount=amount_received_dai, usd_value=ZERO),
            location_label=scroll_accounts[0],
            notes=f'Receive {amount_received_dai} DAI in syncswap from {scroll_accounts[0]}',
            counterparty=CPT_SYNCSWAP,
            address=SYNCSWAP_VAULT_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('scroll_accounts', [['0xc3CF2BFE223E0003aeA138F79b6c0b256eF3a3B8']])
def test_scroll_syncswap_add_liquidity_usdc_eth(database, scroll_inquirer, scroll_accounts):
    evmhash = deserialize_evm_tx_hash('0x53b49fb4098473d9138e4d3afef81c2012ff6a80dba849d38b6d9314734eec97')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=scroll_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    timestamp = TimestampMS(1714678119000)
    fee = FVal('0.000155563689015168')
    amount_usdc = FVal('7.214098')
    amount_usdc_approved = FVal('115792089237316195423570985008687907853269984665640564039457584007913129.639935')  # noqa: E501
    amount_eth = FVal('0.001')
    pool_address = '0x814A23B053FD0f102AEEda0459215C2444799C70'
    lp_token_identifier = evm_address_to_identifier(
        address=pool_address,
        chain_id=ChainID.SCROLL,
        token_type=EvmTokenKind.ERC20,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=fee, usd_value=ZERO),
            location_label=scroll_accounts[0],
            notes=f'Burned {fee} ETH for gas',
            counterparty='gas',
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(amount=amount_eth),
            location_label=scroll_accounts[0],
            notes=f'Deposit {amount_eth} ETH to syncswap LP {pool_address}',
            counterparty=CPT_SYNCSWAP,
            address=SYNCSWAP_ROUTER_ADDRESS,
            extra_data={'pool_address': pool_address},
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=57,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken(USDC_SCROLL_EIP155),
            balance=Balance(amount=amount_usdc_approved),
            location_label=scroll_accounts[0],
            notes=f'Set USDC spending approval of {scroll_accounts[0]} by 0x80e38291e06339d10AAB483C65695D004dBD5C69 to {amount_usdc_approved}',  # noqa: E501
            address=SYNCSWAP_ROUTER_ADDRESS,
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=58,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=EvmToken(USDC_SCROLL_EIP155),
            balance=Balance(amount=amount_usdc),
            location_label=scroll_accounts[0],
            notes=f'Deposit {amount_usdc} USDC to syncswap LP {pool_address}',
            counterparty=CPT_SYNCSWAP,
            address=SYNCSWAP_VAULT_ADDRESS,
            extra_data={'pool_address': pool_address},
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=61,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken(lp_token_identifier),
            balance=Balance(amount=FVal(7.5831095273E-8), usd_value=FVal(0)),
            location_label=scroll_accounts[0],
            notes='Receive 0.000000075831095273 USDC/WETH cSLP from syncswap pool',
            counterparty='syncswap',
            address=ZERO_ADDRESS,
        ),

    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('scroll_accounts', [['0xCCc94fc5CE75b57EE727eB34BF41794e91b9348f']])
def test_scroll_syncswap_remove_stable_pool_liquidity(database, scroll_inquirer, scroll_accounts):
    evmhash = deserialize_evm_tx_hash('0x1b97fb5ae56ab4e62de86f469f6bf0a9415c37a22d846461d72c3f7ad4c580b1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=scroll_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    timestamp = TimestampMS(1714775828000)
    fee = FVal('0.000099013637479223')
    amount_usdc = FVal('3.714525')
    amount_usdt = FVal('4.28265')
    pool_address = '0x2076d4632853FB165Cf7c7e7faD592DaC70f4fe1'
    lp_token_identifier = evm_address_to_identifier(
        address=pool_address,
        chain_id=ChainID.SCROLL,
        token_type=EvmTokenKind.ERC20,
    )
    amount_lp_token = FVal('6.838365025357646228')
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=fee, usd_value=ZERO),
            location_label=scroll_accounts[0],
            notes=f'Burned {fee} ETH for gas',
            counterparty='gas',
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=10,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken(lp_token_identifier),
            balance=Balance(amount=amount_lp_token),
            location_label=scroll_accounts[0],
            notes=f'Send {amount_lp_token} USDC/USDT sSLP to syncswap pool',
            counterparty=CPT_SYNCSWAP,
            address=string_to_evm_address(pool_address),
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=EvmToken(USDC_SCROLL_EIP155),
            balance=Balance(amount=amount_usdc),
            location_label=scroll_accounts[0],
            notes=f'Remove {amount_usdc} USDC from syncswap LP {pool_address}',
            counterparty=CPT_SYNCSWAP,
            address=string_to_evm_address(SYNCSWAP_VAULT_ADDRESS),
            extra_data={'pool_address': pool_address},
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=15,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=EvmToken(USDT_SCROLL_EIP155),
            balance=Balance(amount=amount_usdt),
            location_label=scroll_accounts[0],
            notes=f'Remove {amount_usdt} USDT from syncswap LP {pool_address}',
            counterparty=CPT_SYNCSWAP,
            address=string_to_evm_address(SYNCSWAP_VAULT_ADDRESS),
            extra_data={'pool_address': pool_address},
        ),
    ]
    assert events == expected_events
