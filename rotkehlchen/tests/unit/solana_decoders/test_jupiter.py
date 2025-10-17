from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.solana.modules.jupiter.constants import CPT_JUPITER
from rotkehlchen.chain.solana.modules.pump_fun.constants import CPT_PUMP_FUN
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
        tx_ref=signature,
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
        tx_ref=signature,
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
        tx_ref=signature,
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
        tx_ref=signature,
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
@pytest.mark.parametrize('solana_accounts', [['DYH6x4JoTXUUc4GJUcBYv4gPRApbfTsoZEeD318ernQY']])
def test_swap_with_temp_token_account(
        solana_inquirer: 'SolanaInquirer',
        solana_accounts: list[SolanaAddress],
) -> None:
    """This swaps from CORL to Wrapped SOL and uses a temporary token account in some of its
    internal transfers, which requires special handling to get the correct owner address."""
    signature = deserialize_tx_signature('53TUfpGbKBGjYNw2w84fXbEDpGGbdo3dLcnJs5sKiL3v3eKAuxTZWCcoXjgzgS3J14bEDEkHJ9qmWnDCLQRwUm5N')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1760110834000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.000006'),
        location_label=solana_accounts[0],
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:EqtNWgVzp77fNMQTNbDwzELmfcKuaiurYhbzLJfqjS72'),
        amount=FVal(spend_amount := '106.347883'),
        location_label=solana_accounts[0],
        notes=f'Swap {spend_amount} CORL in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('solana/token:So11111111111111111111111111111111111111112'),
        amount=FVal(receive_amount := '0.029137025'),
        location_label=solana_accounts[0],
        notes=f'Receive {receive_amount} SOL as the result of a swap in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY']])
def test_rfq_swap(
        solana_inquirer: 'SolanaInquirer',
        solana_accounts: list[SolanaAddress],
) -> None:
    signature = deserialize_tx_signature('5vBFfTGrcdkE7ZdsUDSU2kRkhoFp4EgKtLLB6h2m1uQoG5wCddCkFGnNjXaHrV2r1kZ8CpJfh7UcWJ9tFXAyKc8Q')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1758217531000)),
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs'),
        amount=FVal(spend_amount := '0.00287442'),
        location_label=solana_accounts[0],
        notes=f'Swap {spend_amount} WETH in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_SOL,
        amount=FVal(receive_amount := '0.052708178'),
        location_label=solana_accounts[0],
        notes=f'Receive {receive_amount} SOL as the result of a swap in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['AV6VwqhnPSPJQU9i4xfHNscNkkm5GYSP4TajCKS4LAhh']])
def test_route_v2(
        solana_inquirer: 'SolanaInquirer',
        solana_accounts: list[SolanaAddress],
) -> None:
    signature = deserialize_tx_signature('5yFvtkWX3G9ANAvXgc9jtd7EgTE6x36XhC81ochM9CFTneBYooP8fSPVN3eyYQFp7361xdGGey8MQ7QfiDGcqBci')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1759678378000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.000034378'),
        location_label=(user_address := solana_accounts[0]),
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:KMNo3nJsBXfcpJTVhZcXLW7RmTwTt4GVFE7suUBo9sS'),
        amount=FVal(spend_amount := '1984.30989'),
        location_label=user_address,
        notes=f'Swap {spend_amount} KMNO in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('3ndjN1nJVUKGrJBc1hhVpER6kWTZKHdyDrPyCJyX3CXK'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=FVal(receive_amount := '171.477013'),
        location_label=user_address,
        notes=f'Receive {receive_amount} USDC as the result of a swap in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('3ndjN1nJVUKGrJBc1hhVpER6kWTZKHdyDrPyCJyX3CXK'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=3,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=FVal(trade_fee_amount := '0.171477'),
        location_label=user_address,
        notes=f'Spend {trade_fee_amount} USDC as Jupiter platform fee',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('3ndjN1nJVUKGrJBc1hhVpER6kWTZKHdyDrPyCJyX3CXK'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['HQd6KuZ1JjHDLkNmsX7dwdobHPZ4VkXHwRCjGenbwCzq']])
def test_route_v2_with_multiple_underlying_swaps(
        solana_inquirer: 'SolanaInquirer',
        solana_accounts: list[SolanaAddress],
) -> None:
    """This swap uses the route_v2 instruction, with multiple underlying swaps in the route that
    are all combined into a single set of swap events. Also uses pump.fun in one of the underlying
    swaps, and has pump.fun fees.

    The route is as follows:
    * 1.71828 USDC -> 0.009015764 WSOL
    * 0.27972 USDC -> BONK -> 0.001458716 WSOL
    * 0.010345617 WSOL -> 66,980.582126 Luminaries

    But not all WSOL is used in the swap to Luminaries (0.009015764 + 0.001458716 < 0.010345617),
    so the swap is actually a multi-trade, with one send event and two receive events
    (USDC -> WSOL and Luminaries).
    """
    signature = deserialize_tx_signature('2nLWcmrav8ZinvmsYz35kh3w5rMo1sokzmHdmkXjYhKYt762n67Q21xEuTG2rGGNJYDJ63nCHWmgXeYL3U8PHasK')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1760635774000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.000733036'),
        location_label=(user_address := solana_accounts[0]),
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=FVal(spend_amount := '1.99800'),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('6n9VhCwQ7EwK6NqFDjnHPzEk6wZdRBTfh43RFgHQWHuQ'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('solana/token:CFJxqK6Wo6CqCwa9RDwvLGUDUz3HYQXT15Lftqnupump'),
        amount=FVal(lum_receive_amount := '66980.582126'),
        location_label=user_address,
        notes=f'Receive {lum_receive_amount} Luminaries as the result of a swap in Jupiter',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('6n9VhCwQ7EwK6NqFDjnHPzEk6wZdRBTfh43RFgHQWHuQ'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=3,
        timestamp=timestamp,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=FVal(trade_fee_amount := '0.002'),
        location_label=user_address,
        notes=f'Spend {trade_fee_amount} USDC as Jupiter platform fee',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('6n9VhCwQ7EwK6NqFDjnHPzEk6wZdRBTfh43RFgHQWHuQ'),
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=4,
        timestamp=timestamp,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('solana/token:So11111111111111111111111111111111111111112'),
        amount=FVal(wsol_receive_amount := '0.000128863'),
        location_label=user_address,
        notes=f'Receive {wsol_receive_amount} SOL due to positive slippage in a Jupiter swap',
        counterparty=CPT_JUPITER,
        address=SolanaAddress('6n9VhCwQ7EwK6NqFDjnHPzEk6wZdRBTfh43RFgHQWHuQ'),
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=5,
        timestamp=timestamp,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('solana/token:So11111111111111111111111111111111111111112'),
        amount=FVal(pump_fee_amount1 := '0.000096195'),
        location_label=user_address,
        notes=f'Spend {pump_fee_amount1} WSOL as Pump.fun protocol fee',
        counterparty=CPT_PUMP_FUN,
        address=SolanaAddress('7VtfL8fvgNfhz17qKRMjzQEXgbdpnHHHQRh54R9jP2RJ'),
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=6,
        timestamp=timestamp,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('solana/token:So11111111111111111111111111111111111111112'),
        amount=FVal(pump_fee_amount2 := '0.000031031'),
        location_label=user_address,
        notes=f'Spend {pump_fee_amount2} WSOL as Pump.fun coin creator fee',
        counterparty=CPT_PUMP_FUN,
        address=SolanaAddress('4M53NgcosencncUqMaWMTu7qt2CeGGLZwNCnou5Q3SLW'),
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
        tx_ref=signature,
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
        tx_ref=signature,
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
        tx_ref=signature,
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
        tx_ref=signature,
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
        tx_ref=signature,
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
        tx_ref=signature,
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
