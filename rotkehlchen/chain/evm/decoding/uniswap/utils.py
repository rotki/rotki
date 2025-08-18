import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT, DecodingOutput
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2, CPT_UNISWAP_V3
from rotkehlchen.chain.evm.decoding.uniswap.v4.constants import V4_SWAP_TOPIC
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def decode_basic_uniswap_info(
        amount_sent: int,
        amount_received: int,
        decoded_events: list['EvmEvent'],
        counterparty: str,
        notify_user: Callable[['EvmEvent', str], None],
        native_currency: 'CryptoAsset',
) -> DecodingOutput:
    """
    Check last three events and if they are related to the swap, label them as such.
    We check three events because potential events are: spend, (optionally) approval, receive.
    Earlier events are not related to the current swap.
    """
    spend_event, approval_event, receive_event = None, None, None
    for event in reversed(decoded_events):
        try:
            crypto_asset = event.asset.resolve_to_crypto_asset()
        except (UnknownAsset, WrongAssetType):
            notify_user(event, counterparty)
            return DEFAULT_DECODING_OUTPUT

        if (
            event.event_type == HistoryEventType.INFORMATIONAL and
            event.event_subtype == HistoryEventSubType.APPROVE and
            approval_event is None
        ):
            approval_event = event
        elif (
            event.amount == asset_normalized_value(amount=amount_sent, asset=crypto_asset) and
            event.event_type == HistoryEventType.SPEND and
            # don't touch native asset since there may be multiple such transfers
            # and they are better handled by the aggregator decoder.
            event.asset != native_currency and
            spend_event is None
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.counterparty = counterparty
            event.notes = f'Swap {event.amount} {crypto_asset.symbol} in {counterparty}'
            spend_event = event
        elif (
            event.amount == asset_normalized_value(amount=amount_received, asset=crypto_asset) and
            event.event_type == HistoryEventType.RECEIVE and
            event.asset != native_currency and
            receive_event is None
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = counterparty
            event.notes = f'Receive {event.amount} {crypto_asset.symbol} as a result of a {counterparty} swap'  # noqa: E501
            receive_event = event
        elif (
            event.counterparty in {CPT_UNISWAP_V2, CPT_UNISWAP_V3} and
            event.event_type == HistoryEventType.TRADE
        ):
            # The structure of swaps is the following:
            # 1.1 Optional approval event
            # 1.2 Optional spend event
            # 1.3 Optional receive event
            # 1.4 SWAP_SIGNATURE event
            # 2.1 Optional approval event
            # 2.2 Optional spend event
            # 2.3 Optional receive event
            # 2.4 SWAP_SIGNATURE event
            # etc.
            # So if we are at SWAP_SIGNATURE № 2 then all events that are before SWAP_SIGNATURE № 1
            # should have already been decoded, have counterparty set and have type Trade.
            break
        else:  # If what described in the comment above is not met then it is an error.
            log.debug(
                f'Found unexpected event {event.serialize()} during decoding a uniswap swap in '
                f'transaction {event.tx_hash.hex()}. Either uniswap router or an aggregator was '
                f'used and decoding needs to happen in the aggregator-specific decoder.',
            )
            break

    # Make sure that the approval event is NOT between the spend and receive events.
    maybe_reshuffle_events(
        ordered_events=[approval_event, spend_event, receive_event],
        events_list=decoded_events,
    )
    return DecodingOutput(process_swaps=True)


def get_uniswap_swap_amounts(tx_log: 'EvmTxReceiptLog') -> tuple[int, int]:
    """Get the amount received and amount sent in a swap from the swap tx_log.

    Uniswap represents the delta of tokens in the pool with a signed integer.
    In V3 the negative delta indicates the amount leaving the pool (the user receives them),
    and positive indicates the amount entering the pool (the user sends them to the pool).
    In V4 this is reversed - negative indicates the amount entering the pool (sent by the user),
    and positive indicates the amount leaving the pool (received by the user).

    The caller is responsible for only calling this function with a swap tx_log.
    Returns a tuple of (amount_received, amount_sent).
    """
    delta_token_0 = int.from_bytes(tx_log.data[0:32], signed=True)
    delta_token_1 = int.from_bytes(tx_log.data[32:64], signed=True)
    if delta_token_0 > 0:
        amount_a, amount_b = delta_token_0, -delta_token_1
    else:
        amount_a, amount_b = delta_token_1, -delta_token_0

    if tx_log.topics[0] == V4_SWAP_TOPIC:
        return amount_a, amount_b

    return amount_b, amount_a  # V3
