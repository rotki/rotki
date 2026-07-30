import inspect
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.api.websockets.typedefs import HistoryEventsStep
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.exchange import HistoryEventQueue
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.types import Location, Timestamp

EXCHANGE_METHODS_TO_CHECK = (
    'query_balances',
    'query_online_deposits_withdrawals',
    'query_online_margin_history',
)


def test_all_methods_implemented():
    """Tests all methods needed by the exchange interface are implemented by all exchanges"""

    for name in SUPPORTED_EXCHANGES:
        module_name = ExchangeManager._get_exchange_module_name(name)
        try:
            module = import_module(f'rotkehlchen.exchanges.{module_name}')
        except ModuleNotFoundError:
            # This should never happen
            raise AssertionError(
                f'Tried to initialize unknown exchange {name}. Should never happen.',
            ) from None

        exchange_object = getattr(module, module_name.capitalize())
        members = inspect.getmembers(exchange_object)
        methods = [x for x in members if x[0] in EXCHANGE_METHODS_TO_CHECK]
        for method_name, method in methods:
            code = inspect.getsource(method)
            msg = f'{method_name} for exchange {name} is not implemented'
            assert 'raise NotImplementedError' not in code, msg


def test_requery_exchange_history_events_uses_incremental_queue() -> None:
    manager = ExchangeManager(msg_aggregator=MagicMock())
    manager.database = MagicMock()
    manager.database.get_settings.return_value = SimpleNamespace(non_syncing_exchanges=set())
    exchange = MagicMock()
    exchange.name = 'test'
    exchange.location = Location.BINANCE
    exchange.location_id.return_value = 'binance_test'
    exchange.requery_online_history_events_into_queue.return_value = Timestamp(2)
    manager.connected_exchanges[Location.BINANCE].append(exchange)
    event_queue = MagicMock(spec=HistoryEventQueue)
    event_queue.queried_events = 3
    event_queue.saved_events = 2

    with patch(
        'rotkehlchen.exchanges.manager.HistoryEventQueue',
        return_value=event_queue,
    ):
        result = manager.requery_exchange_history_events(
            location=Location.BINANCE,
            name='test',
            start_ts=Timestamp(1),
            end_ts=Timestamp(2),
        )

    exchange.requery_online_history_events_into_queue.assert_called_once_with(
        start_ts=Timestamp(1),
        end_ts=Timestamp(2),
        event_queue=event_queue,
    )
    event_queue.flush.assert_called_once_with()
    assert result == (3, 2, 1, Timestamp(2))


def test_requery_exchange_history_events_flushes_and_finishes_on_error() -> None:
    manager = ExchangeManager(msg_aggregator=MagicMock())
    manager.database = MagicMock()
    manager.database.get_settings.return_value = SimpleNamespace(non_syncing_exchanges=set())
    exchange = MagicMock()
    exchange.name = 'test'
    exchange.location = Location.BINANCE
    exchange.location_id.return_value = 'binance_test'
    exchange.requery_online_history_events_into_queue.side_effect = RemoteError('query failed')
    manager.connected_exchanges[Location.BINANCE].append(exchange)
    event_queue = MagicMock(spec=HistoryEventQueue)

    with (
        patch(
            'rotkehlchen.exchanges.manager.HistoryEventQueue',
            return_value=event_queue,
        ),
        pytest.raises(RemoteError, match='query failed'),
    ):
        manager.requery_exchange_history_events(
            location=Location.BINANCE,
            name='test',
            start_ts=Timestamp(1),
            end_ts=Timestamp(2),
        )

    event_queue.flush.assert_called_once_with()
    assert exchange.send_history_events_status_msg.call_args_list[-1].kwargs == {
        'step': HistoryEventsStep.QUERYING_EVENTS_FINISHED,
    }


def test_query_exchange_history_events_continues_after_remote_error() -> None:
    manager = ExchangeManager(msg_aggregator=MagicMock())
    manager.database = MagicMock()
    manager.database.get_settings.return_value = SimpleNamespace(non_syncing_exchanges=set())
    exchanges = [MagicMock(), MagicMock()]
    for idx, exchange in enumerate(exchanges):
        exchange.name = f'test_{idx}'
        exchange.location = Location.BINANCE
        exchange.location_id.return_value = f'binance_test_{idx}'
    exchanges[0].query_history_events.side_effect = RemoteError('first failed')
    exchanges[1].query_history_events.side_effect = RemoteError('second failed')
    manager.connected_exchanges[Location.BINANCE].extend(exchanges)

    with pytest.raises(
        RemoteError,
        match=(
            'Failed to query binance history events for '
            'test_0: first failed, test_1: second failed'
        ),
    ):
        manager.query_exchange_history_events(location=Location.BINANCE, name=None)

    for exchange in exchanges:
        exchange.query_history_events.assert_called_once_with()


def test_query_exchange_history_events_should_continue_after_input_error() -> None:
    manager = ExchangeManager(msg_aggregator=MagicMock())
    manager.database = MagicMock()
    manager.database.get_settings.return_value = SimpleNamespace(non_syncing_exchanges=set())
    exchanges = [MagicMock(), MagicMock()]
    for idx, exchange in enumerate(exchanges):
        exchange.name = f'test_{idx}'
        exchange.location = Location.BINANCE
        exchange.location_id.return_value = f'binance_test_{idx}'
    exchanges[0].query_history_events.side_effect = InputError('no market pairs selected')
    manager.connected_exchanges[Location.BINANCE].extend(exchanges)

    with pytest.raises(
        RemoteError,
        match='Failed to query binance history events for test_0: no market pairs selected',
    ):
        manager.query_exchange_history_events(location=Location.BINANCE, name=None)

    for exchange in exchanges:
        exchange.query_history_events.assert_called_once_with()


def test_query_exchange_history_events_should_propagate_named_input_error() -> None:
    manager = ExchangeManager(msg_aggregator=MagicMock())
    manager.database = MagicMock()
    manager.database.get_settings.return_value = SimpleNamespace(non_syncing_exchanges=set())
    exchange = MagicMock()
    exchange.name = 'test'
    exchange.location = Location.BINANCE
    exchange.location_id.return_value = 'binance_test'
    exchange.query_history_events.side_effect = InputError('no market pairs selected')
    manager.connected_exchanges[Location.BINANCE].append(exchange)

    with pytest.raises(InputError, match='no market pairs selected'):
        manager.query_exchange_history_events(location=Location.BINANCE, name='test')

    exchange.query_history_events.assert_called_once_with()
