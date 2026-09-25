import pytest

from rotkehlchen.api.websockets.typedefs import UserMessageEntry, UserMessageRecord
from rotkehlchen.types import Location
from rotkehlchen.user_messages import BadData, LocalDbProblem


@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_query_user_message(rotkehlchen_api_server, websocket_connection):
    """User messages carry key/subject/fields over a real socket, and a message about no
    single location sends its subject as null while keeping its key and fields."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.msg_aggregator.add_warning(
        'Tag foo with invalid color code found in the DB. Skipping tag',
        classification=LocalDbProblem(entry=UserMessageEntry.TAG),
    )
    rotki.msg_aggregator.add_error(
        'Failed to deserialize a kucoin balance. Ignoring it.',
        classification=BadData(record=UserMessageRecord.BALANCE, error='Missing key: amount'),
        subject=Location.KUCOIN,
    )
    websocket_connection.wait_until_messages_num(num=2, timeout=10)
    assert websocket_connection.messages_num() == 2
    assert websocket_connection.pop_message() == {'type': 'user_message', 'data': {
        'verbosity': 'warning',
        'value': 'Tag foo with invalid color code found in the DB. Skipping tag',
        'key': 'local_db',
        'subject': None,
        'fields': {'entry': 'tag'},
    }}
    assert websocket_connection.pop_message() == {'type': 'user_message', 'data': {
        'verbosity': 'error',
        'value': 'Failed to deserialize a kucoin balance. Ignoring it.',
        'key': 'bad_data',
        'subject': 'kucoin',
        'fields': {'record': 'balance', 'error': 'Missing key: amount'},
    }}
    assert websocket_connection.messages_num() == 0
