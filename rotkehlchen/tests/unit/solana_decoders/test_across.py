from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.across.constants import CPT_ACROSS
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.solana import get_decoded_events_of_solana_tx
from rotkehlchen.types import SolanaAddress, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY']])
def test_across_fill_from_arbitrum(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    signature = deserialize_tx_signature('3bg38hZgFD5xwnwf3gj3oik8F22kF3GtKZmQd3bj1syK7b9GCNqbGKnir4XuhjUXhpe4qQbeYPZjCzowLUH17Rx1')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=TimestampMS(1762471062000),
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=FVal('119.656776'),
        location_label=(recipient := solana_accounts[0]),
        notes='Bridge 119.656776 USDC from Arbitrum One to Solana via Across',
        counterparty=CPT_ACROSS,
        address=SolanaAddress('CBG4RpoLqM1KJk9q3d3MeCwE9RgqeAWbwntUREPB1jUF'),
        extra_data={'bridge': {
            'from_chain': 42161,
            'to_chain': 'solana',
            'from_address': '0x56a1A34F0d33788ebA53e2706854A37A5F275536',
            'to_address': recipient,
            'transfer_id': '3982708',
        }},
    )]
