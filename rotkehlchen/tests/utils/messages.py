from typing import TYPE_CHECKING, Any

from rotkehlchen.api.websockets.typedefs import DeliveryPolicy, WSMessageType, delivery_of

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.user_messages import HeldMessage, MessagesAggregator


def _drain(
        msg_aggregator: MessagesAggregator,
        select: Callable[[HeldMessage], bool],
) -> list[HeldMessage]:
    """Remove the held messages `select` picks, once per time each was sent.

    Tests read what a client would have been told one send at a time, so a message held
    with a count is repeated count times. The client itself gets it once, with the count.
    """
    with msg_aggregator._lock:
        held = msg_aggregator._drain_locked(select)
    return [message for message in held for _ in range(message.count)]


def _is_user_warning(message: HeldMessage) -> bool:
    return (
        message.payload['type'] == WSMessageType.USER_MESSAGE and
        message.payload['data']['verbosity'] == 'warning'
    )


def _is_failure(message: HeldMessage) -> bool:
    """A user error, or a structured failure held as a report. Events such as a CSV import
    result and state such as a premium status change are not failures."""
    message_type, data = WSMessageType(message.payload['type']), message.payload['data']
    if message_type == WSMessageType.USER_MESSAGE:
        return data['verbosity'] == 'error'
    return delivery_of(message_type, data).policy == DeliveryPolicy.REPORT


def consume_warnings(msg_aggregator: MessagesAggregator) -> list[str]:
    """Drain the held user warnings as their newest rendered sentence."""
    return [message.text for message in _drain(msg_aggregator, _is_user_warning)]


def consume_errors(msg_aggregator: MessagesAggregator) -> list[str]:
    """Drain the held failures as text: the newest sentence of a user error, the
    serialized payload of a report."""
    return [message.text for message in _drain(msg_aggregator, _is_failure)]


def consume_error_payloads(msg_aggregator: MessagesAggregator) -> list[dict[str, Any]]:
    """Like consume_errors, as the `{type, data}` objects the websocket sends."""
    return [message.payload for message in _drain(msg_aggregator, _is_failure)]


def no_message_errors(msg_aggregator: MessagesAggregator) -> None:
    errors = consume_errors(msg_aggregator)
    warnings = consume_warnings(msg_aggregator)
    assert len(errors) == 0, f'Found errors: {errors}'
    assert len(warnings) == 0, f'Found warnings: {warnings}'


def consume_errors_and_unknown_assets(
        msg_aggregator: MessagesAggregator,
) -> tuple[list[str], list[str]]:
    """Drain the polled errors as (user error texts, unknown exchange asset identifiers).

    Without a websocket client the reported failures are held with the user errors, so an
    exchange asset rotki can't map shows up there too. Any other failure type fails.
    """
    errors, unknown_assets = [], []
    for payload in consume_error_payloads(msg_aggregator):
        if payload['type'] == 'exchange_unknown_asset':
            unknown_assets.append(payload['data']['identifier'])
        else:
            assert payload['type'] == 'user_message', f'Unexpected message {payload}'
            errors.append(payload['data']['value'])
    return errors, unknown_assets
