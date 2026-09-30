from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.user_messages import MessagesAggregator


def no_message_errors(msg_aggregator) -> None:
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
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
    for payload in msg_aggregator.consume_error_payloads():
        if payload['type'] == 'exchange_unknown_asset':
            unknown_assets.append(payload['data']['identifier'])
        else:
            assert payload['type'] == 'user_message', f'Unexpected message {payload}'
            errors.append(payload['data']['value'])
    return errors, unknown_assets
