from typing import Any
from unittest.mock import patch

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.types import Timestamp


def test_entry_strict_unique_id_prefers_tid_over_hash() -> None:
    """Fills include a `tid` that is unique per fill; prefer it over the hash
    (which can be the shared L1 tx hash).
    """
    entry = {'tid': 118906512037719, 'hash': '0xabc', 'oid': 90542681, 'time': 1000}
    assert HyperliquidAPI._entry_strict_unique_id(entry) == '118906512037719'


def test_entry_strict_unique_id_uses_hash_when_no_tid() -> None:
    """Funding and non-funding ledger entries don't have `tid`; hash is unique."""
    entry = {'hash': '0xdeadbeef', 'oid': 90542681, 'time': 1000}
    assert HyperliquidAPI._entry_strict_unique_id(entry) == '0xdeadbeef'


def test_entry_strict_unique_id_ignores_oid_alone() -> None:
    """`oid` is shared across partial fills of one order, so it must not be
    used on its own as a unique identifier.
    """
    entry = {'oid': 90542681, 'time': 1000}
    assert HyperliquidAPI._entry_strict_unique_id(entry) is None


def test_entry_unique_id_falls_back_to_time() -> None:
    """The public _entry_unique_id always returns a non-empty string; when no
    tid/hash is present it defensively uses the entry time.
    """
    entry = {'time': 1700000000000}
    assert HyperliquidAPI._entry_unique_id(entry) == '1700000000000'


def test_iter_entries_does_not_collapse_partial_fills_sharing_oid() -> None:
    """Two partial fills of the same order share `oid` but have distinct
    `tid`s and occur at the same millisecond. They must both be yielded.
    """
    api = HyperliquidAPI()
    address = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')
    same_time = 1700000000000
    shared_oid = 90542681
    fill_a: dict[str, Any] = {
        'tid': 1, 'oid': shared_oid, 'hash': '0xtx', 'time': same_time, 'sz': '4',
    }
    fill_b: dict[str, Any] = {
        'tid': 2, 'oid': shared_oid, 'hash': '0xtx', 'time': same_time, 'sz': '6',
    }

    with patch.object(api, '_query_list', side_effect=[[fill_a, fill_b], []]):
        contexts = list(api._iter_entries_by_time(
            query_type='userFillsByTime',
            address=address,
            start_ts=Timestamp(1),
            end_ts=Timestamp(2),
        ))

    yielded_tids = [ctx.entry['tid'] for ctx in contexts]
    assert yielded_tids == [1, 2]


def test_iter_entries_dedups_same_tid_across_pages() -> None:
    """When the same entry is returned in two overlapping pages, we keep only
    one copy via the tid-based dedup key.
    """
    api = HyperliquidAPI()
    address = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')
    duplicate_fill: dict[str, Any] = {
        'tid': 42, 'oid': 1, 'hash': '0xtx', 'time': 1700000000000, 'sz': '1',
    }

    # Page 1 returns the entry, page 2 returns it again (overlapping window),
    # page 3 is empty and terminates pagination.
    with patch.object(api, '_query_list', side_effect=[
        [duplicate_fill],
        [duplicate_fill],
        [],
    ]):
        contexts = list(api._iter_entries_by_time(
            query_type='userFillsByTime',
            address=address,
            start_ts=Timestamp(1699999999),
            end_ts=Timestamp(1700000000),
        ))

    assert len(contexts) == 1


def test_iter_entries_recovers_truncated_boundary_entries() -> None:
    """When a page contains entries spanning multiple milliseconds and the
    oldest ms had additional entries truncated by the API page cap, the next
    query is repeated at that boundary so the remaining entries can be
    fetched. Per-entry dedup prevents already-yielded entries from being
    emitted twice.
    """
    api = HyperliquidAPI()
    address = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')
    boundary_ts = 1700000000000
    newer_fill: dict[str, Any] = {
        'tid': 1, 'oid': 1, 'hash': '0xtx', 'time': boundary_ts + 10, 'sz': '1',
    }
    boundary_fill_a: dict[str, Any] = {
        'tid': 2, 'oid': 2, 'hash': '0xtx', 'time': boundary_ts, 'sz': '2',
    }
    boundary_fill_b: dict[str, Any] = {
        'tid': 3, 'oid': 3, 'hash': '0xtx', 'time': boundary_ts, 'sz': '3',
    }
    older_fill: dict[str, Any] = {
        'tid': 4, 'oid': 4, 'hash': '0xtx', 'time': boundary_ts - 5, 'sz': '4',
    }

    # Page 1: newer + boundary_a (boundary_b is truncated by the page cap).
    # Page 2: re-queried with endTime=boundary, returns boundary_a (deduped),
    #         boundary_b (new — recovered), and an older entry.
    # Page 3: empty, terminates pagination.
    with patch.object(api, '_query_list', side_effect=[
        [newer_fill, boundary_fill_a],
        [boundary_fill_a, boundary_fill_b, older_fill],
        [],
    ]):
        contexts = list(api._iter_entries_by_time(
            query_type='userFillsByTime',
            address=address,
            start_ts=Timestamp(1699999998),
            end_ts=Timestamp(1700000001),
        ))

    assert [ctx.entry['tid'] for ctx in contexts] == [1, 2, 3, 4]
