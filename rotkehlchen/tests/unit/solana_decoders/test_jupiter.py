from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.solana.modules.jupiter.constants import CPT_JUPITER
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.solana_swap import SolanaSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.constants import A_SOL
from rotkehlchen.tests.utils.solana import get_decoded_events_of_solana_tx
from rotkehlchen.types import SolanaAddress, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['FvTqiyvB52rmV82jj9Wc5efLyuWht9vprr8bivDBzGnV']])
def test_swap_token_to_token(
        solana_inquirer: 'SolanaInquirer',
        solana_accounts: list[SolanaAddress],
) -> None:
    signature = deserialize_tx_signature('4G1gvudg2PyQV17v8agjHKYJQA9bxxJtMWEvKzk1Lb9k5yHTj3dnrvDGEiaDT7qSYePvswBrUq1bC5j4iPbk5gzQ')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        signature=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1760110834000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=(gas_amount := FVal('0.000005')),
        location_label=(user := solana_accounts[0]),
        notes=f'Spend {gas_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(
        signature=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=(jito_tip_amount := FVal('0.000021')),
        location_label=user,
        notes=f'Send {jito_tip_amount} SOL to yTzJEkfUJCRDvktpvz1qiBZ1wcvgWXoXSX3tRZ33yZd',
        address=SolanaAddress('yTzJEkfUJCRDvktpvz1qiBZ1wcvgWXoXSX3tRZ33yZd'),
    ), SolanaSwapEvent(
        signature=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=(out_amount := FVal('500')),
        location_label=user,
        notes=f'Swap {out_amount} USDC in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('FeLULW5RCKDT2NuThu4vrAQ8BjH5YbU2Y7GbiZXYohm8'),
    ), SolanaSwapEvent(
        signature=signature,
        sequence_index=3,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('solana/token:9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump'),
        amount=(in_amount := FVal('812.420478')),
        location_label=user,
        notes=f'Receive {in_amount} FARTCOIN as the result of a swap in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('FeLULW5RCKDT2NuThu4vrAQ8BjH5YbU2Y7GbiZXYohm8'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['E2MPTDnFPNiCRmbJGKYSYew48NWRGVNfHjoiibFP5VL2']])
def test_arbitrage_swap(
        solana_inquirer: 'SolanaInquirer',
        solana_accounts: list[SolanaAddress],
) -> None:
    """This transaction has two jupiter swap route instructions. In the first one it swaps
    BONK -> USDC -> SOL, and in the second it simply swaps SOL -> BONK. The intermediate USDC swap
    is hidden, only showing the result of the full route instruction.
    """
    signature = deserialize_tx_signature('5acNq9XFxMxEzLWTR7hC2v6iNGbXxwChqR5mP2KkfkLvB6LAzTMpVDNSY7yaq4EbU7ypywKtpfLZgLQqDnwfeX8P')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        signature=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1760010360000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=(gas_amount := FVal('0.000005')),
        location_label=(user := solana_accounts[0]),
        notes=f'Spend {gas_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(  # TODO: decode this as a jito tip: https://github.com/orgs/rotki/projects/11/views/3?pane=issue&itemId=133200023
        signature=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=(jito_tip_amount := FVal('0.000001')),
        location_label=user,
        notes=f'Send {jito_tip_amount} SOL to DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh',
        address=SolanaAddress('DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh'),
    ), SolanaSwapEvent(
        signature=signature,
        sequence_index=8,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'),
        amount=(out_amount_1 := FVal('455257.98707')),
        location_label=user,
        notes=f'Swap {out_amount_1} BONK in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('9MkixYmjT2UbMgnNnPBTYkRjzdmi4zP1jkMdCkR89L67'),
    ), SolanaSwapEvent(
        signature=signature,
        sequence_index=9,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('solana/token:So11111111111111111111111111111111111111112'),
        amount=(in_amount_2 := FVal('0.039404601')),
        location_label=user,
        notes=f'Receive {in_amount_2} SOL as the result of a swap in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('9MkixYmjT2UbMgnNnPBTYkRjzdmi4zP1jkMdCkR89L67'),
    ), SolanaSwapEvent(
        signature=signature,
        sequence_index=10,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:So11111111111111111111111111111111111111112'),
        amount=(out_amount_3 := FVal('0.039406767')),
        location_label=user,
        notes=f'Swap {out_amount_3} SOL in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('GtpsrTHYnfFVm3qkPJtyKVwQLpXT7p2MRy9bp5hYeJnQ'),
    ), SolanaSwapEvent(
        signature=signature,
        sequence_index=11,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('solana/token:DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'),
        amount=(in_amount_3 := FVal('455331.87102')),
        location_label=user,
        notes=f'Receive {in_amount_3} BONK as the result of a swap in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('GtpsrTHYnfFVm3qkPJtyKVwQLpXT7p2MRy9bp5hYeJnQ'),
    )]
