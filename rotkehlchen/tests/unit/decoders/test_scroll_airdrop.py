from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.scroll.constants import CPT_SCROLL
from rotkehlchen.chain.scroll.modules.scroll_airdrop.constants import (
    A_SCR,
    SCROLL_TOKEN_DISTRIBUTOR,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('scroll_accounts', [['0xe247D2F39923E12C66f08b9C03a8E231087BDEFa']])
def test_claim_scroll_airdop(
        scroll_inquirer: 'ScrollInquirer',
        scroll_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x7adb39abe532e0310840486ad9f03068d5a2fc7983f16e5cca16ff2be3899429')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, airdrop_amount = scroll_accounts[0], TimestampMS(1729588449000), '0.00001063050890817', '106.1909'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=64,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_SCR,
            balance=Balance(amount=FVal(airdrop_amount)),
            location_label=user_address,
            notes=f'Claim {airdrop_amount} SCR from scroll airdrop',
            counterparty=CPT_SCROLL,
            address=SCROLL_TOKEN_DISTRIBUTOR,
            extra_data={'airdrop_identifier': 'scroll'},
        ),
    ]
