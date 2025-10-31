import logging
import traceback
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Optional, overload

from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import AnyBlockchainAddress, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.history.events.structures.solana_event import SolanaEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def decode_transfer_direction(
        from_address: AnyBlockchainAddress,
        to_address: AnyBlockchainAddress | None,
        tracked_accounts: Sequence[AnyBlockchainAddress],
        maybe_get_exchange_fn: Callable[[AnyBlockchainAddress], str | None],
) -> tuple[HistoryEventType, HistoryEventSubType, str | None, AnyBlockchainAddress, str, str] | None:  # noqa: E501
    """Determine how to classify a transfer event depending on if the addresses are tracked,
    if they are exchange addresses, etc.

    Returns event type, event subtype, location label, address, counterparty and verb.
    address is the address on the opposite side of the event. counterparty is the exchange name
    if it is a deposit / withdrawal to / from an exchange.
    """
    tracked_from = from_address in tracked_accounts
    tracked_to = to_address in tracked_accounts if to_address is not None else False
    if not tracked_from and not tracked_to:
        return None

    from_exchange = maybe_get_exchange_fn(from_address)
    to_exchange = maybe_get_exchange_fn(to_address) if to_address else None

    counterparty: str | None = None
    event_subtype = HistoryEventSubType.NONE
    if tracked_from and tracked_to:
        event_type = HistoryEventType.TRANSFER
        location_label = from_address
        address = to_address
        verb = 'Transfer'
    elif tracked_from:
        if to_exchange is not None:
            event_type = HistoryEventType.DEPOSIT
            verb = 'Deposit'
            counterparty = to_exchange
            event_subtype = HistoryEventSubType.DEPOSIT_ASSET
        else:
            event_type = HistoryEventType.SPEND
            verb = 'Send'

        address = to_address
        location_label = from_address
    else:  # can only be tracked_to
        if from_exchange:
            event_type = HistoryEventType.WITHDRAWAL
            verb = 'Withdraw'
            counterparty = from_exchange
            event_subtype = HistoryEventSubType.REMOVE_ASSET
        else:
            event_type = HistoryEventType.RECEIVE
            verb = 'Receive'

        address = from_address
        location_label = to_address  # type: ignore  # to_address can't be None here

    return event_type, event_subtype, location_label, address, counterparty, verb  # type: ignore


def decode_safely(
        handled_exceptions: tuple[type[Exception], ...],
        msg_aggregator: 'MessagesAggregator',
        blockchain: SupportedBlockchain,
        func: Callable,
        tx_reference: str | None = None,
        *args: tuple[Any],
        **kwargs: Any,
) -> tuple[Any, bool]:
    """
    Wrapper for methods that execute logic from decoders. It handles all known errors
    by logging them and optionally sending them to the user.

    tx_reference is used only to log more information in case of error when decoding
    a single transaction.

    It returns a tuple where the first argument is the output of func and the second is a boolean
    set to True if an error was raised from func.
    """
    try:
        return func(*args, **kwargs), False
    except handled_exceptions as e:
        log.error(traceback.format_exc())
        error_prefix = (
            f'Decoding of transaction {tx_reference} in {blockchain}'
            if tx_reference is not None else
            f'Post processing of decoded events in {blockchain}'
        )
        log.error(
            f'{error_prefix} failed due to {e} '
            f'when calling {func.__name__} with {args=} {kwargs=}',
        )
        msg_aggregator.add_error(f'{error_prefix} failed. Check logs for more details')

    return None, True


@overload
def maybe_reshuffle_events(
        ordered_events: Sequence[Optional['EvmEvent']],
        events_list: list['EvmEvent'],
) -> None:
    ...


@overload
def maybe_reshuffle_events(
        ordered_events: Sequence[Optional['SolanaEvent']],
        events_list: list['SolanaEvent'],
) -> None:
    ...


def maybe_reshuffle_events(
        ordered_events: Sequence[Optional['EvmEvent']] | Sequence[Optional['SolanaEvent']],
        events_list: list['EvmEvent'] | list['SolanaEvent'],
) -> None:
    """Updates the sequence indexes of the events in `events_list` to be in ascending order as
    specified by the order of `ordered_events`. The actual order of the events in the list
    is updated via `sort` later in the decoding process, so is not changed here.

    Reshuffling is for two reasons.
    1. So that it appears uniformly in the UI
    2. So that during accounting we know which type of event comes first in a swap-like event.

    For example, for swaps we expect two consecutive events with the first
    being the out event and the second the in event.

    The events are optional since it's also possible they may not be found.
    """
    if len(actual_events := [x for x in ordered_events if x is not None]) <= 1:
        return  # nothing to do

    max_seq_index = -1
    for event in events_list:
        if event not in actual_events:
            max_seq_index = max(event.sequence_index, max_seq_index)

    for idx, event in enumerate(actual_events):
        event.sequence_index = max_seq_index + idx + 1
