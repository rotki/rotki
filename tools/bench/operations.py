"""Registry of measured operations (design §4.1).

An operation is a single timed API interaction against an unlocked backend.
Criteria for inclusion: user-visible, deterministic on a seeded profile, no
network egress. ``boot_to_ping`` and ``user_unlock`` are measured by the block
driver in harness.py, not here, since their timing brackets differ.

PnL/accounting operations are deliberately absent until the accounting rework
lands (design §4.1).
"""
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from tools.bench.runner import BackendRunner

EVENTS_PAGE_SIZE: Final = 50


@dataclass(frozen=True)
class Operation:
    name: str
    profiles: tuple[str, ...]  # profiles this operation runs on
    run: Callable[['BackendRunner', dict[str, Any]], None]  # (backend, expected.json)


def _history_events_p1(backend: 'BackendRunner', _expected: dict[str, Any]) -> None:
    backend.request('POST', '/history/events', {
        'limit': EVENTS_PAGE_SIZE,
        'offset': 0,
    })


def _history_events_deep(backend: 'BackendRunner', expected: dict[str, Any]) -> None:
    backend.request('POST', '/history/events', {
        'limit': EVENTS_PAGE_SIZE,
        'offset': int(expected['total_events'] * 2 / 3),
    })


def _history_events_filtered(backend: 'BackendRunner', _expected: dict[str, Any]) -> None:
    backend.request('POST', '/history/events', {
        'limit': EVENTS_PAGE_SIZE,
        'offset': 0,
        'counterparties': ['uniswap-v3'],
        'asset': 'ETH',
    })


def _history_events_by_location(backend: 'BackendRunner', _expected: dict[str, Any]) -> None:
    backend.request('POST', '/history/events', {
        'limit': EVENTS_PAGE_SIZE,
        'offset': 0,
        'location': 'kraken',
    })


def _asset_search(backend: 'BackendRunner', _expected: dict[str, Any]) -> None:
    backend.request('POST', '/assets/search/levenshtein', {
        'value': 'usd',
        'limit': 50,
    })


def _manual_balances(backend: 'BackendRunner', _expected: dict[str, Any]) -> None:
    # valuation resolves via the manual latest prices seeded by the profiles
    backend.request('GET', '/balances/manual')


def _netvalue_stats(backend: 'BackendRunner', _expected: dict[str, Any]) -> None:
    # reads the seeded timed_location_data snapshots
    backend.request('GET', '/statistics/netvalue')


OPERATIONS: Final = (
    Operation(
        name='history_events_p1',
        profiles=('small', 'whale'),
        run=_history_events_p1,
    ),
    Operation(
        name='history_events_deep',
        profiles=('whale',),
        run=_history_events_deep,
    ),
    Operation(
        name='history_events_filtered',
        profiles=('whale',),
        run=_history_events_filtered,
    ),
    Operation(
        name='history_events_by_location',
        profiles=('whale',),
        run=_history_events_by_location,
    ),
    Operation(
        name='asset_search',
        profiles=('small', 'whale'),
        run=_asset_search,
    ),
    Operation(
        name='manual_balances',
        profiles=('small', 'whale'),
        run=_manual_balances,
    ),
    Operation(
        name='netvalue_stats',
        profiles=('small', 'whale'),
        run=_netvalue_stats,
    ),
)
