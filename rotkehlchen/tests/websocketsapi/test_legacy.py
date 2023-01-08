import gevent
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


def _send_stuff(msg_aggregator, websocket_connection):
    for _ in range(10):
        # We need big strings in order to replicate. Small messages do not hit it
        msg_aggregator.add_error('x' * 1000000)
        msg_aggregator.add_warning('y' * 100000)
        if websocket_connection.messages_num() != 0:
            websocket_connection.pop_message()


@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_websockets_concurrent_use(rotkehlchen_api_server, websocket_connection):
    """Up until 1.26.3 there was no lock per websocket connection and that could under
    very heavy and specific circumstances cause concurrent websocket access from multiple
    greenlets.

    This test replicates that scenario and it fails before the addition of the lock.
    Serves as a regression test.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    g1 = gevent.spawn(_send_stuff, rotki.msg_aggregator, websocket_connection)
    _send_stuff(rotki.msg_aggregator, websocket_connection)
    g2 = gevent.spawn(_send_stuff, rotki.msg_aggregator, websocket_connection)
    gevent.joinall([g1, g2])
    assert all(
        isinstance(x.exception, gevent.exceptions.ConcurrentObjectUseError) is False
        for x in rotki.greenlet_manager.greenlets
    ), 'At least one ConcurrentObjectUseError exception happened'
