from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.cctp.constants import CPT_CCTP
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
@pytest.mark.parametrize('solana_accounts', [['DUZeRN6fpJKjVKMtiidk3Xf34kA8J41yjtktaXs3Y3ei']])
def test_cctp_v2_deposit_to_base(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    signature = deserialize_tx_signature('4SNhUZz3FBijWYTqo35w414DaT1EfX3Whc931CcJRq5Vm7BMeW8VGTAq11DFmbLaT21Vg4Ds48eqr2oAXXZTXN6U')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1788256838000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal('0.00001'),
        location_label=(depositor := solana_accounts[0]),
        notes='Spend 0.00001 SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=FVal('7.27'),
        location_label=depositor,
        notes='Bridge 7.27 USDC from Solana to Base via CCTP',
        counterparty=CPT_CCTP,
        extra_data={'bridge': {
            'from_chain': 'solana',
            'to_chain': 8453,
            'from_address': depositor,
            'to_address': '0x34B741a3D0ef8c8ef6dd490C305c5C5ca20aCa59',
        }},
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['3NLEELDx3wvAtX1PcFteWRyNNJiKqA73QNnAnb9H852D']])
def test_cctp_v2_receive_from_ethereum(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    signature = deserialize_tx_signature('eTsg8KMXGG5pgLRtXGrJcrGAGNa18xQMm6Pt2ERHhuCGUKiPiFzfVU8pF4vVTKeAb8rAKNBNLLyosJdbMHx3Tp2')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=TimestampMS(1774849772000),
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=FVal('148.745446'),
        location_label=solana_accounts[0],
        notes='Bridge 148.745446 USDC from Ethereum to Solana via CCTP',
        counterparty=CPT_CCTP,
        address=SolanaAddress('E1bQJ8eMMn3zmeSewW3HQ8zmJr7KR75JonbwAtWx2bux'),
        extra_data={'bridge': {
            'from_chain': 1,
            'to_chain': 'solana',
            'from_address': '0xD156fFB54871F4562744d6Be5d6321B5BffCa3B6',
            'to_address': '3WzSRoiRj7GwrMzavq1Hu2TRQX2Y2qTVftnXeGZsxPUF',
            'transfer_id': '0x12ddf131fa86823e6247b1b71df376725044217ee3aca8b7d522235a44b5ad1b',
        }},
    )]
