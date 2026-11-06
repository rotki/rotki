from unittest.mock import MagicMock

from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.bucket_state import BucketRunState
from rotkehlchen.types import TimestampMS


def _event(identifier: int, timestamp: int) -> MagicMock:
    return MagicMock(identifier=identifier, timestamp=TimestampMS(timestamp))


def _state() -> BucketRunState[str]:
    return BucketRunState[str](make_key=lambda bucket: ('l', bucket, '', 'A'))


def test_awaiting_bucket_is_stopped_at_the_event() -> None:
    state = _state()
    state.await_reconciliation('b', event := _event(1, 100), FVal(1), FVal(-1))

    assert state.is_awaiting_reconciliation('b')
    assert state.negative_event('b') is event
    assert state.stops['l', 'b', '', 'A'].event_identifier == 1


def test_failure_is_reported_once_per_wait() -> None:
    state = _state()
    state.await_reconciliation('b', _event(1, 100), FVal(1), FVal(-1))

    assert state.report_failure_once('b') is True
    assert state.report_failure_once('b') is False


def test_reconcile_clears_wait_stop_and_report_together() -> None:
    state = _state()
    state.await_reconciliation('b', _event(1, 100), FVal(1), FVal(-1))
    state.report_failure_once('b')

    state.reconcile('b')

    assert not state.is_awaiting_reconciliation('b')
    assert state.negative_event('b') is None
    assert len(state.stops) == 0
    state.await_reconciliation('b', _event(2, 200), FVal(1), FVal(-1))
    assert state.report_failure_once('b') is True


def test_stop_recorded_while_awaiting_overwrites_stop_but_keeps_waiting() -> None:
    state = _state()
    state.await_reconciliation('b', _event(1, 100), FVal(1), FVal(-1))

    state.record_stop('b', _event(2, 200), FVal(0), FVal(-2))

    assert state.is_awaiting_reconciliation('b')
    assert state.stops['l', 'b', '', 'A'].event_identifier == 2


def test_plain_stop_is_not_awaiting_reconciliation() -> None:
    state = _state()
    state.record_stop('b', _event(1, 100), FVal(1), FVal(-1))

    assert not state.is_awaiting_reconciliation('b')
    assert len(state.stops) == 1
