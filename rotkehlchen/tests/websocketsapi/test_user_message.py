import pytest

from rotkehlchen.api.websockets.typedefs import UserMessageRecord
from rotkehlchen.types import Location
from rotkehlchen.user_messages import BadData


@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_query_user_message(rotkehlchen_api_server, websocket_connection):
    """User messages carry key/subject/fields over a real socket.

    An emitter that has not been classified yet sends them as null rather than omitting
    them, so it is visibly unclassified instead of looking like a message predating the
    fields.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.msg_aggregator.add_error('This is an error')
    rotki.msg_aggregator.add_warning('This is a warning')
    rotki.msg_aggregator.add_error(
        'Failed to deserialize a kucoin balance. Ignoring it.',
        classification=BadData(record=UserMessageRecord.BALANCE, error='Missing key: amount'),
        subject=Location.KUCOIN,
    )
    websocket_connection.wait_until_messages_num(num=3, timeout=10)
    assert websocket_connection.messages_num() == 3
    assert websocket_connection.pop_message() == {'type': 'user_message', 'data': {
        'verbosity': 'error',
        'value': 'This is an error',
        'key': None,
        'subject': None,
        'fields': None,
    }}
    assert websocket_connection.pop_message() == {'type': 'user_message', 'data': {
        'verbosity': 'warning',
        'value': 'This is a warning',
        'key': None,
        'subject': None,
        'fields': None,
    }}
    assert websocket_connection.pop_message() == {'type': 'user_message', 'data': {
        'verbosity': 'error',
        'value': 'Failed to deserialize a kucoin balance. Ignoring it.',
        'key': 'bad_data',
        'subject': 'kucoin',
        'fields': {'record': 'balance', 'error': 'Missing key: amount'},
    }}
    assert websocket_connection.messages_num() == 0
