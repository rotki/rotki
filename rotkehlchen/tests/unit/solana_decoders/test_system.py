from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_SOL
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.solana import get_decoded_events_of_solana_tx
from rotkehlchen.types import SolanaAddress, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [
    ['4DrfzUpTdNtfr7D1RBVw2WhPshasifw97mH3aj27Skp9'],
    ['3AmPaYAe6xWFxci4iCe8m2TkrQFZJPaj5AeBPTDoeFkR'],
    ['4DrfzUpTdNtfr7D1RBVw2WhPshasifw97mH3aj27Skp9', '3AmPaYAe6xWFxci4iCe8m2TkrQFZJPaj5AeBPTDoeFkR'],  # noqa: E501
])
def test_native_transfer(
        solana_inquirer: 'SolanaInquirer',
        solana_accounts: list[SolanaAddress],
) -> None:
    """Check that native transfers are decoded correctly.
    Tests three scenarios:
    * Both addresses tracked, decoded as fee event, transfer event.
    * Only sender tracked, decoded as fee event, spend event.
    * Only receiver tracked, decoded as a receive event only.
    """
    signature = deserialize_tx_signature('2RrXcP3MMgjjt46SJ34wT4pXKhCV94psPJnZgVyVRkPZpk5JSmCMgFyd1rwKuz3LMTAi3hhay11N41YPtodav81z')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    transfer_amount, spend_address, receive_address = '0.718759267', SolanaAddress('4DrfzUpTdNtfr7D1RBVw2WhPshasifw97mH3aj27Skp9'), SolanaAddress('3AmPaYAe6xWFxci4iCe8m2TkrQFZJPaj5AeBPTDoeFkR')  # noqa: E501
    fee_event = SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1759436023000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.000005'),
        location_label=spend_address,
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    )
    if len(solana_accounts) == 2:
        assert events == [fee_event, SolanaEvent(
            tx_ref=signature,
            sequence_index=1,
            timestamp=timestamp,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_SOL,
            amount=FVal(transfer_amount),
            location_label=spend_address,
            notes=f'Transfer {transfer_amount} SOL to {receive_address}',
            address=receive_address,
        )]
    elif solana_accounts == [spend_address]:
        assert events == [fee_event, SolanaEvent(
            tx_ref=signature,
            sequence_index=1,
            timestamp=timestamp,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_SOL,
            amount=FVal(transfer_amount),
            location_label=spend_address,
            notes=f'Send {transfer_amount} SOL to {receive_address}',
            address=receive_address,
        )]
    elif solana_accounts == [receive_address]:
        assert events == [SolanaEvent(
            tx_ref=signature,
            sequence_index=0,
            timestamp=timestamp,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_SOL,
            amount=FVal(transfer_amount),
            location_label=receive_address,
            notes=f'Receive {transfer_amount} SOL from {spend_address}',
            address=spend_address,
        )]
