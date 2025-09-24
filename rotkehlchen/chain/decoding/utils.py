from collections.abc import Callable, Sequence

from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import AnyBlockchainAddress


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
