import pytest


@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_query_legacy_message(rotkehlchen_api_server, websocket_connection):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.msg_aggregator.add_error('This is an error')
    rotki.msg_aggregator.add_warning('This is a warning')
    websocket_connection.wait_until_messages_num(num=2, timeout=10)
    assert websocket_connection.messages_num() == 2
    msg1 = websocket_connection.pop_message()
    assert msg1 == {'type': 'legacy', 'data': {'verbosity': 'error', 'value': 'This is an error'}}
    msg2 = websocket_connection.pop_message()
    assert msg2 == {'type': 'legacy', 'data': {'verbosity': 'warning', 'value': 'This is a warning'}}  # noqa: E501
    assert websocket_connection.messages_num() == 0
