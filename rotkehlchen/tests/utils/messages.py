from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.user_messages import MessagesAggregator


def no_message_errors(msg_aggregator: MessagesAggregator) -> None:
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0, f'Found errors: {errors}'
    assert len(warnings) == 0, f'Found warnings: {warnings}'
