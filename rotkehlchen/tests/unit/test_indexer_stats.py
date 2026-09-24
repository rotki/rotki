import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from rotkehlchen import indexer_stats
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.externalapis.routescan import Routescan
from rotkehlchen.sigil import create_sigil_events_batch, submit_sigil_batch
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChainID


@pytest.fixture(name='use_clean_caching_directory')
def fixture_use_clean_caching_directory() -> bool:
    return True


def _events(batch: list) -> list[dict]:
    return [entry['payload'] for entry in batch]


def _wait_for_release(started: threading.Event, release: threading.Event, **_kwargs) -> bool:
    started.set()
    return release.wait(2)


def test_indexer_usage_aggregates_periodic_and_final_windows(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr(indexer_stats, 'time', SimpleNamespace(monotonic=lambda: now[0]))
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    submit = MagicMock(return_value=True)
    monkeypatch.setattr(indexer_stats, 'submit_sigil_batch', submit)
    stats = indexer_stats.IndexerStats()

    now[0] += indexer_stats.INDEXER_ANALYTICS_INTERVAL
    stats.maybe_flush()
    submit.assert_not_called()
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
    stats.record('blockscout', ChainID.OPTIMISM, 'rpc.eth_call')
    now[0] += indexer_stats.INDEXER_ANALYTICS_INTERVAL
    stats.maybe_flush()
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
    now[0] += 30 * 60
    stats.close()

    events = [event for call in submit.call_args_list for event in _events(call.kwargs['batch'])]
    assert [event['name'] for event in events] == ['indexer_requests'] * 2
    windows = [event['data'] for event in events]
    assert [
        (window['window'], window['requests'], window['seconds'], window['final'])
        for window in windows
    ] == [
        (1, 3, 7200, False), (2, 1, 1800, True),
    ]
    assert all('hours' not in window for window in windows)
    assert windows[0]['by_indexer'] == {
        'etherscan': {'1': {'account.txlist': 2}},
        'blockscout': {'10': {'rpc.eth_call': 1}},
    }
    assert windows[1]['by_indexer'] == {'etherscan': {'1': {'account.txlist': 1}}}
    assert windows[0]['session_id'] == windows[1]['session_id']


def test_indexer_usage_retries_failed_batch_and_discards_on_opt_out(monkeypatch) -> None:
    consent = [True]
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: consent[0])
    submit = MagicMock(side_effect=[False, True])
    monkeypatch.setattr(indexer_stats, 'submit_sigil_batch', submit)
    stats = indexer_stats.IndexerStats()
    stats.record('routescan', ChainID.ETHEREUM, 'account.txlistinternal')
    stats._window_start -= indexer_stats.INDEXER_ANALYTICS_INTERVAL
    stats.maybe_flush()
    assert stats._worker is not None
    stats._worker.join()
    stats.close()
    assert submit.call_args_list[0].kwargs['batch'] == submit.call_args_list[1].kwargs['batch']

    stats = indexer_stats.IndexerStats()
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
    consent[0] = False
    stats.discard()
    consent[0] = True
    stats.close()
    assert submit.call_count == 2
    assert stats._close_worker is None


def test_indexer_usage_drops_failed_batches_without_blocking_later_windows(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr(indexer_stats, 'time', SimpleNamespace(monotonic=lambda: now[0]))
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    submit = MagicMock(return_value=False)
    monkeypatch.setattr(indexer_stats, 'submit_sigil_batch', submit)
    stats = indexer_stats.IndexerStats()

    for _ in range(2):
        stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
        now[0] += indexer_stats.INDEXER_ANALYTICS_INTERVAL
        stats.maybe_flush()
        assert stats._worker is not None
        stats._worker.join(timeout=2)

    stats.maybe_flush()  # The five-minute retry delay still applies.
    assert submit.call_count == 2
    for _ in range(3):
        now[0] += indexer_stats.INDEXER_ANALYTICS_RETRY_DELAY
        stats.maybe_flush()
        assert stats._worker is not None
        stats._worker.join(timeout=2)

    assert [
        _events(call.kwargs['batch'])[0]['data']['window']
        for call in submit.call_args_list
    ] == [1, 1, 1, 2, 2, 2]
    assert len(stats._pending) == 0


def test_indexer_usage_unexpected_upload_errors_use_bounded_retries(monkeypatch, caplog) -> None:
    now = [100.0]
    monkeypatch.setattr(indexer_stats, 'time', SimpleNamespace(monotonic=lambda: now[0]))
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    submit = MagicMock(side_effect=ValueError('broken upload'))
    monkeypatch.setattr(indexer_stats, 'submit_sigil_batch', submit)
    stats = indexer_stats.IndexerStats()
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
    now[0] += indexer_stats.INDEXER_ANALYTICS_INTERVAL

    with caplog.at_level(logging.ERROR, logger='rotkehlchen.indexer_stats'):
        for attempt in range(indexer_stats.INDEXER_ANALYTICS_MAX_ATTEMPTS):
            stats.maybe_flush()
            assert stats._worker is not None
            stats._worker.join(timeout=2)
            assert submit.call_count == attempt + 1
            stats.maybe_flush()
            assert submit.call_count == attempt + 1
            now[0] += indexer_stats.INDEXER_ANALYTICS_RETRY_DELAY

    assert len(stats._pending) == 0
    assert 'Failed to submit indexer usage analytics' in caplog.text


def test_indexer_usage_retries_after_worker_start_fails(monkeypatch) -> None:
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    monkeypatch.setattr(indexer_stats, 'submit_sigil_batch', MagicMock(return_value=True))
    stats = indexer_stats.IndexerStats()
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
    stats._window_start -= indexer_stats.INDEXER_ANALYTICS_INTERVAL

    with (
        patch.object(indexer_stats.Task, 'start', side_effect=RuntimeError('no threads')),
        pytest.raises(RuntimeError, match='no threads'),
    ):
        stats.maybe_flush()

    assert vars(stats)['_worker'] is None
    stats.maybe_flush()
    worker = stats._worker
    assert worker is not None
    worker.join(timeout=2)
    assert len(stats._pending) == 0


def test_indexer_usage_close_ignores_worker_start_failure(monkeypatch, caplog) -> None:
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    stats = indexer_stats.IndexerStats()
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')

    with (
        patch.object(indexer_stats.Task, 'start', side_effect=RuntimeError('no threads')),
        caplog.at_level(logging.ERROR, logger='rotkehlchen.indexer_stats'),
    ):
        stats.close()

    assert stats._closed is True
    assert stats._close_worker is None
    assert 'Failed to start indexer analytics close upload' in caplog.text


def test_indexer_usage_is_disabled_in_source_builds(monkeypatch) -> None:
    monkeypatch.setattr(indexer_stats, 'is_production', lambda: False)
    with patch.object(indexer_stats.CachedSettings, 'get_entry') as get_entry:
        stats = indexer_stats.IndexerStats()
        stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
        stats.maybe_flush()
        stats.close()

    assert len(stats._counts) == 0
    assert stats._worker is None
    assert stats._close_worker is None
    get_entry.assert_not_called()


def test_indexer_usage_checks_production_status_once_per_instance(monkeypatch) -> None:
    is_production = MagicMock(return_value=True)
    get_entry = MagicMock(return_value=True)
    monkeypatch.setattr(indexer_stats, 'is_production', is_production)
    monkeypatch.setattr(indexer_stats.CachedSettings, 'get_entry', get_entry)
    stats = indexer_stats.IndexerStats()

    for _ in range(5):
        stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')

    is_production.assert_called_once_with()
    # Mutable consent is still rechecked on both sides of the lock.
    assert get_entry.call_count == 10
    assert sum(stats._counts.values()) == 5


@pytest.mark.parametrize('close', [False, True])
def test_indexer_usage_worker_error_is_logged(monkeypatch, caplog, close: bool) -> None:
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    stats = indexer_stats.IndexerStats()
    stats._window_start -= indexer_stats.INDEXER_ANALYTICS_INTERVAL
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')

    with (
        patch.object(stats, '_send_pending', side_effect=RuntimeError('upload failed')),
        caplog.at_level(logging.ERROR, logger='rotkehlchen.indexer_stats'),
    ):
        if close:
            stats.start_close()
            worker = stats._close_worker
        else:
            stats.maybe_flush()
            worker = stats._worker
        assert worker is not None
        worker.join(timeout=2)

    assert isinstance(worker.exception, RuntimeError)
    assert f'{worker.task_name} failed' in caplog.text
    assert 'RuntimeError: upload failed' in caplog.text
    assert any(record.threadName == worker.task_name for record in caplog.records)


def test_indexer_usage_opt_out_skips_recording_and_discard(monkeypatch) -> None:
    # Consent changes before record takes the lock.
    consent_checks = iter((True, False, False, False, False))
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: next(consent_checks))  # noqa: E501
    stats = indexer_stats.IndexerStats()
    with patch.object(stats, 'discard') as discard:
        stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
        assert len(stats._counts) == 0
        stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
        stats.maybe_flush()
        discard.assert_not_called()
    stats.close()
    assert stats._close_worker is None


def test_indexer_usage_opt_out_does_not_wait_for_started_upload(monkeypatch) -> None:
    consent = [True]
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: consent[0])
    started, release = threading.Event(), threading.Event()
    monkeypatch.setattr(
        indexer_stats, 'submit_sigil_batch', partial(_wait_for_release, started, release),
    )
    stats = indexer_stats.IndexerStats()
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
    stats._window_start -= indexer_stats.INDEXER_ANALYTICS_INTERVAL
    stats.maybe_flush()
    assert started.wait(2)

    consent[0] = False
    with ThreadPoolExecutor(max_workers=1) as pool:
        stopping = pool.submit(stats.discard)
        try:
            stopping.result(timeout=0.25)
            assert len(stats._counts) == 0
            assert len(stats._pending) == 0
        finally:
            release.set()

    assert stats._worker is not None
    stats._worker.join(timeout=2)
    assert len(stats._counts) == 0
    assert len(stats._pending) == 0


def test_indexer_usage_counts_concurrent_requests(monkeypatch) -> None:
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    submit = MagicMock(return_value=True)
    monkeypatch.setattr(indexer_stats, 'submit_sigil_batch', submit)
    stats = indexer_stats.IndexerStats()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(
            lambda _: stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist'),
            range(1000),
        ))
    stats.close()
    events = _events(submit.call_args.kwargs['batch'])
    assert len(events) == 1
    assert events[0]['data']['requests'] == 1000
    assert events[0]['data']['by_indexer'] == {'etherscan': {'1': {'account.txlist': 1000}}}


def test_indexer_usage_close_overlaps_cleanup_and_is_bounded(monkeypatch) -> None:
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    monkeypatch.setattr(indexer_stats, 'INDEXER_ANALYTICS_CLOSE_TIMEOUT', 0.25)
    started, release = threading.Event(), threading.Event()
    submit = MagicMock(side_effect=partial(_wait_for_release, started, release))
    monkeypatch.setattr(indexer_stats, 'submit_sigil_batch', submit)
    stats = indexer_stats.IndexerStats()
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')

    start = time.monotonic()
    stats.start_close()
    assert started.wait(1)
    assert 0 < submit.call_args.kwargs['timeout'] <= 0.25
    time.sleep(0.3)  # Other logout work proceeds while the upload is still waiting.
    stats.wait_for_close()
    assert time.monotonic() - start < 1
    release.set()
    assert stats._close_worker is not None
    stats._close_worker.join()


def test_indexer_usage_wait_for_close_uses_remaining_deadline(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr(indexer_stats, 'time', SimpleNamespace(monotonic=lambda: now[0]))
    stats = object.__new__(indexer_stats.IndexerStats)
    stats._close_worker = MagicMock()
    stats._close_deadline = 107.0

    stats.wait_for_close()

    stats._close_worker.join.assert_called_once_with(timeout=7.0)


def test_indexer_usage_periodic_upload_finishes_final_window_during_close(monkeypatch) -> None:
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    started, release = threading.Event(), threading.Event()
    submit = MagicMock(side_effect=partial(_wait_for_release, started, release))
    monkeypatch.setattr(indexer_stats, 'submit_sigil_batch', submit)
    stats = indexer_stats.IndexerStats()
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
    stats._window_start -= indexer_stats.INDEXER_ANALYTICS_INTERVAL
    stats.maybe_flush()
    assert started.wait(2)

    stats.record('blockscout', ChainID.OPTIMISM, 'rpc.eth_call')
    upload_lock = stats._upload_lock
    # Force the close worker to lose the lock race; the periodic worker must send the final window.
    with patch.object(stats, '_upload_lock') as close_lock:
        close_lock.acquire.return_value = False
        close_lock.release.side_effect = upload_lock.release
        stats.start_close()
        release.set()
        stats.wait_for_close()
        assert stats._worker is not None
        stats._worker.join(timeout=2)
        assert stats._close_worker is not None
        stats._close_worker.join(timeout=2)

    assert [
        _events(call.kwargs['batch'])[0]['data']['final']
        for call in submit.call_args_list
    ] == [False, True]
    assert len(stats._pending) == 0


def test_indexer_usage_logs_close_lock_timeout(monkeypatch, caplog) -> None:
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    monkeypatch.setattr(indexer_stats, 'INDEXER_ANALYTICS_CLOSE_TIMEOUT', 0.1)
    started, release = threading.Event(), threading.Event()
    monkeypatch.setattr(
        indexer_stats, 'submit_sigil_batch', partial(_wait_for_release, started, release),
    )
    stats = indexer_stats.IndexerStats()
    stats.record('etherscan', ChainID.ETHEREUM, 'account.txlist')
    stats._window_start -= indexer_stats.INDEXER_ANALYTICS_INTERVAL
    stats.maybe_flush()
    assert started.wait(2)

    stats.record('blockscout', ChainID.OPTIMISM, 'rpc.eth_call')
    with caplog.at_level(logging.DEBUG, logger='rotkehlchen.indexer_stats'):
        stats.close()
        assert stats._close_worker is not None
        stats._close_worker.join(timeout=2)
    release.set()
    assert stats._worker is not None
    stats._worker.join(timeout=2)
    assert 'close upload timed out waiting for an active upload' in caplog.text


def test_sigil_batch_submission_checks_http_result(monkeypatch) -> None:
    batch = create_sigil_events_batch([('example', '/test', {'requests': 1})])
    post_mock = MagicMock(return_value=SimpleNamespace(ok=False))
    monkeypatch.setattr(requests, 'post', post_mock)
    assert submit_sigil_batch(batch, timeout=5) is False
    assert post_mock.call_args.kwargs['json'] == batch

    post_mock.side_effect = requests.ConnectionError()
    assert submit_sigil_batch(batch, timeout=5) is False


def test_indexer_http_attempts_include_retries_and_normalize_blockscout_paths(
        monkeypatch,
        database,
        messages_aggregator,
) -> None:
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    submit = MagicMock(return_value=True)
    monkeypatch.setattr(indexer_stats, 'submit_sigil_batch', submit)
    stats = indexer_stats.IndexerStats()
    with patch.object(Etherscan, 'detect_api_key_tier'):
        etherscan = Etherscan(database, messages_aggregator, indexer_stats=stats)
    routescan = Routescan(database, messages_aggregator, indexer_stats=stats)
    blockscout = Blockscout(database, messages_aggregator, indexer_stats=stats)

    monkeypatch.setattr(etherscan._rate_limiter, 'acquire', lambda: None)
    monkeypatch.setattr(etherscan, '_handle_rate_limit', lambda **kwargs: 2)
    monkeypatch.setattr(etherscan.session, 'get', MagicMock(side_effect=[
        MockResponse(429, ''),
        MockResponse(200, '{"status":"1","message":"OK","result":[]}'),
    ]))
    assert etherscan._query(ChainID.ETHEREUM, 'account', 'txlist') == []

    monkeypatch.setattr(routescan._rate_limiter, 'acquire', lambda: None)
    monkeypatch.setattr(routescan.session, 'get', MagicMock(return_value=MockResponse(
        200, '{"status":"1","message":"OK","result":[]}',
    )))
    assert routescan._query(ChainID.OPTIMISM, 'account', 'txlistinternal') == []

    monkeypatch.setattr(blockscout._rate_limiter, 'acquire', lambda: None)
    monkeypatch.setattr(blockscout, '_get_url', lambda chain_id, endpoint='api': 'https://example.test/api')
    monkeypatch.setattr(blockscout, '_get_api_key_for_chain', lambda chain_id: None)
    monkeypatch.setattr(blockscout.session, 'request', MagicMock(side_effect=[
        MockResponse(200, '{"status":"1","message":"OK","result":[]}'),
        MockResponse(200, '{"items":[]}'),
        MockResponse(200, '{"result":"0x1"}'),
    ]))
    assert blockscout._query(ChainID.ETHEREUM, 'account', 'txlistinternal') == []
    assert blockscout._query_v2(
        ChainID.ETHEREUM,
        'addresses',
        '0xSecretAddress',
        'withdrawals',
    ) == {'items': []}
    assert blockscout._query_rpc_method(ChainID.ETHEREUM, 'eth_blockNumber') == '0x1'

    stats.close()
    batch = submit.call_args.kwargs['batch']
    assert len(batch) == 1
    assert _events(batch)[0]['data']['by_indexer'] == {
        'etherscan': {'1': {'account.txlist': 2}},
        'routescan': {'10': {'account.txlistinternal': 1}},
        'blockscout': {'1': {
            'account.txlistinternal': 1,
            'v2/addresses/:id/withdrawals': 1,
            'rpc.eth_blockNumber': 1,
        }},
    }
    assert '0xSecretAddress' not in str(batch)


def test_blockscout_skipped_request_is_not_counted(
        monkeypatch,
        database,
        messages_aggregator,
) -> None:
    monkeypatch.setattr(indexer_stats.IndexerStats, '_has_consent', lambda self: True)
    submit = MagicMock(return_value=True)
    monkeypatch.setattr(indexer_stats, 'submit_sigil_batch', submit)
    stats = indexer_stats.IndexerStats()
    blockscout = Blockscout(database, messages_aggregator, indexer_stats=stats)
    monkeypatch.setattr(blockscout, '_get_api_key', lambda: None)
    with pytest.raises(RemoteError, match='no API key configured'):
        blockscout._query(ChainID.ETHEREUM, 'account', 'txlist')
    stats.close()
    submit.assert_not_called()
    assert stats._close_worker is None
