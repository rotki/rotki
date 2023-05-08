from typing import Any, NamedTuple, Optional, Union
import pytest
from rotkehlchen.api.websockets.typedefs import WSMessageType

from rotkehlchen.user_messages import MessagesAggregator


class MockedWsMessage(NamedTuple):
    type: WSMessageType
    data: Union[dict[str, Any], list[Any]]


class MockRotkiNotifier():
    def __init__(self) -> None:
        self.messages: list[MockedWsMessage] = []

    def broadcast(  # pylint: disable=unused-argument
            self,
            message_type: 'WSMessageType',
            to_send_data: Union[dict[str, Any], list[Any]],
            **kwargs: Any,
    ) -> None:
        self.messages.append(MockedWsMessage(type=message_type, data=to_send_data))

    def pop_message(self) -> Optional[MockedWsMessage]:
        if len(self.messages) == 0:
            return None

        return self.messages.pop(0)

    def reset(self) -> None:
        self.messages = []


@pytest.fixture(name='function_scope_initialize_mock_rotki_notifier')
def fixture_function_scope_initialize_mock_rotki_notifier() -> bool:
    return False


@pytest.fixture(scope='session', name='initialize_mock_rotki_notifier')
def fixture_initialize_mock_rotki_notifier() -> bool:
    return False


@pytest.fixture()
def function_scope_messages_aggregator(function_scope_initialize_mock_rotki_notifier):
    msg_aggregator = MessagesAggregator()
    if function_scope_initialize_mock_rotki_notifier is True:
        msg_aggregator.rotki_notifier = MockRotkiNotifier()
    return msg_aggregator


@pytest.fixture(scope='session')
def messages_aggregator(initialize_mock_rotki_notifier):
    msg_aggregator = MessagesAggregator()
    if initialize_mock_rotki_notifier is True:
        msg_aggregator.rotki_notifier = MockRotkiNotifier()
    return msg_aggregator
