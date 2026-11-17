from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.etherfi.constants import CPT_ETHERFI
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_OPTIMISM, LOCATION_SCROLL
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer

CASHBACK_PAYER = string_to_evm_address('0xef55eC694B0B8273967f28627C5BC26F5deea836')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('scroll_accounts', [['0x0520a3bcF7a29EE3FB2DaCC1d50C2D6A6F58Bf1F']])
def test_card_cashback_scroll(
        scroll_inquirer: ScrollInquirer,
        scroll_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xe9d19395a77c8c32295328a4ea15d1af2fa39d1dc9970e18de1dbae997bc9ede')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=10,
        timestamp=TimestampMS(1762884881000),
        location=LOCATION_SCROLL,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.CASHBACK,
        asset=Asset('eip155:534352/erc20:0xd29687c813D741E2F938F4aC377128810E217b1b'),
        amount=FVal(amount := '2.170484754468739741'),
        location_label=scroll_accounts[0],
        notes=f'Receive cashback of {amount} SCR from ether.fi card',
        counterparty=CPT_ETHERFI,
        address=CASHBACK_PAYER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xcd15598eF84e8BeeBf80ec6Dd933554CF36dB321']])
def test_card_cashback_optimism(
        optimism_inquirer: OptimismInquirer,
        optimism_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x91ffc68371de9f501b015805e49d1cb8201b7da7dd36b2b6adae032123463c58')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    usdc = Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85')
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=47,
        timestamp=(timestamp := TimestampMS(1788537151000)),
        location=LOCATION_OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=usdc,
        amount=FVal(spent := '2.178977'),
        location_label=optimism_accounts[0],
        notes=f'Send {spent} USDC from {optimism_accounts[0]} to 0x50A233C4a0Bb1d7124b0224880037d35767a501C',  # noqa: E501
        address=string_to_evm_address('0x50A233C4a0Bb1d7124b0224880037d35767a501C'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=57,
        timestamp=timestamp,
        location=LOCATION_OPTIMISM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.CASHBACK,
        asset=usdc,
        amount=FVal(amount := '0.139653'),
        location_label=optimism_accounts[0],
        notes=f'Receive cashback of {amount} USDC from ether.fi card',
        counterparty=CPT_ETHERFI,
        address=CASHBACK_PAYER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('scroll_accounts', [['0x9fae78d538E39C79Ae74075f01eF34267A750304']])
def test_pending_cashback_cleared_scroll(
        scroll_inquirer: ScrollInquirer,
        scroll_accounts: list[ChecksumEvmAddress],
) -> None:
    """A card spend that also pays out cashback deferred from an earlier spend."""
    tx_hash = deserialize_evm_tx_hash('0xc9489481ae0aa0f7866ed38e6e8358d27f54c23533c863dc8105360b67e78992')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=tx_hash)
    weth = Asset('eip155:534352/erc20:0x5300000000000000000000000000000000000004')
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1775572916000)),
        location=LOCATION_SCROLL,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:534352/erc20:0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4'),
        amount=FVal(spent := '8.8'),
        location_label=scroll_accounts[0],
        notes=f'Send {spent} USDC from {scroll_accounts[0]} to 0x50A233C4a0Bb1d7124b0224880037d35767a501C',  # noqa: E501
        address=string_to_evm_address('0x50A233C4a0Bb1d7124b0224880037d35767a501C'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=LOCATION_SCROLL,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.CASHBACK,
        asset=weth,
        amount=FVal(deferred := '0.00138636527373749'),
        location_label=scroll_accounts[0],
        notes=f'Receive cashback of {deferred} WETH from ether.fi card',
        counterparty=CPT_ETHERFI,
        address=CASHBACK_PAYER,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=LOCATION_SCROLL,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.CASHBACK,
        asset=weth,
        amount=FVal(amount := '0.000127202735990928'),
        location_label=scroll_accounts[0],
        notes=f'Receive cashback of {amount} WETH from ether.fi card',
        counterparty=CPT_ETHERFI,
        address=CASHBACK_PAYER,
    )]
