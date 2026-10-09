import logging
import operator
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.chain.evm.constants import ZERO_32_BYTES_HEX
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset, UnknownCounterpartyMapping
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.tests.utils.hyperliquid import query_history_events
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

ADDRESS = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')
SUBACCOUNT = string_to_evm_address('0x000000000000000000000000000000000000dEaD')
RANGE_START_MS = 1700000000000


class FakeHistoryEndpoint:
    """Serve a fixed history like the Hyperliquid API does for the history endpoints.

    The live API returns the oldest `cap` entries between the inclusive `startTime` and
    `endTime`, in ascending order. The `slice` and `order` arguments make it misbehave in
    the ways the pager has to detect or tolerate. Every requested window is recorded.
    """

    def __init__(
            self,
            entries: list[dict[str, Any]],
            cap: int,
            slice_: Literal['oldest', 'newest'] = 'oldest',
            order: Literal['ascending', 'descending'] = 'ascending',
            ignore_start: bool = False,
    ) -> None:
        self.entries = entries
        self.cap = cap
        self.slice = slice_
        self.order = order
        self.ignore_start = ignore_start
        self.windows: list[tuple[int, int]] = []

    def __call__(
            self,
            payload: dict[str, Any],
            query_name: str,
            wait_for_rate_limit: bool = False,
    ) -> list[dict[str, Any]]:
        self.windows.append((start := payload['startTime'], end := payload['endTime']))
        in_window = sorted(
            (entry for entry in self.entries if (self.ignore_start or start <= entry['time']) and entry['time'] <= end),  # noqa: E501
            key=operator.itemgetter('time'),
        )
        page = in_window[:self.cap] if self.slice == 'oldest' else in_window[-self.cap:]
        return page[::-1] if self.order == 'descending' else page


def _fill(tid: int, time_offset: int) -> dict[str, Any]:
    return {'tid': tid, 'oid': tid, 'hash': '0xtx', 'time': RANGE_START_MS + time_offset}


def _page_tids(
        api: HyperliquidAPI,
        endpoint: FakeHistoryEndpoint,
        end_ts: int = 1700000010,
) -> list[list[int]]:
    """Page through the fake endpoint with a page cap equal to its own and return the tids."""
    with (
        patch('rotkehlchen.externalapis.hyperliquid.HYPERLIQUID_MIN_PAGE_CAP', endpoint.cap),
        patch.object(api, '_query_list', side_effect=endpoint),
    ):
        return [[context.entry['tid'] for context in page] for page in api._iter_entry_pages(
            query_type='userFillsByTime',
            address=ADDRESS,
            start_ts=Timestamp(RANGE_START_MS // 1000),
            end_ts=Timestamp(end_ts),
        )]


def test_entry_strict_unique_id_prefers_tid_over_hash() -> None:
    """Fills include a `tid` that is unique per fill; prefer it over the hash
    (which can be the shared L1 tx hash).
    """
    entry = {'tid': 118906512037719, 'hash': '0xabc', 'oid': 90542681, 'time': 1000}
    assert HyperliquidAPI._entry_strict_unique_id(entry, ADDRESS) == '118906512037719'


def test_entry_strict_unique_id_uses_hash_when_no_tid() -> None:
    """Funding and non-funding ledger entries don't have `tid`; hash is unique."""
    entry = {'hash': '0xdeadbeef', 'oid': 90542681, 'time': 1000}
    assert HyperliquidAPI._entry_strict_unique_id(entry=entry, address=ADDRESS) == '0xdeadbeef'


def test_entry_strict_unique_id_ignores_oid_alone() -> None:
    """`oid` is shared across partial fills of one order, so it must not be
    used on its own as a unique identifier.
    """
    entry = {'oid': 90542681, 'time': 1000}
    assert HyperliquidAPI._entry_strict_unique_id(entry=entry, address=ADDRESS) is None


def test_funding_entries_are_identified_by_time_and_coin() -> None:
    """Funding entries all have the zero hash, which identified every funding payment of
    every user as the same entry, so only the first one was ever saved. Payments at the
    same time for different coins must stay distinct."""
    zero_hash = '0x' + '0' * 64
    btc, eth = ({'time': 1762300800000, 'hash': zero_hash, 'delta': {'type': 'funding', 'coin': coin, 'usdc': '1'}} for coin in ('BTC', 'ETH'))  # noqa: E501
    assert HyperliquidAPI._entry_unique_id(entry=btc, address=ADDRESS) == f'funding_{ADDRESS}_1762300800000_BTC'  # noqa: E501
    assert HyperliquidAPI._entry_unique_id(entry=eth, address=ADDRESS) == f'funding_{ADDRESS}_1762300800000_ETH'  # noqa: E501
    with patch.object(api := HyperliquidAPI(), '_query_list', side_effect=[[btc, eth], []]):
        assert len({context.group_identifier for page in api._iter_entry_pages(
            query_type='userFunding',
            address=ADDRESS,
            start_ts=Timestamp(1762300800),
            end_ts=Timestamp(1762300801),
        ) for context in page}) == 2


def test_entry_unique_id_falls_back_to_address_time_and_content() -> None:
    """The public _entry_unique_id always returns a non-empty string; when no
    tid/hash is present it defensively uses the address, the entry time and its content,
    which includes zero hash entries that are not funding. Distinct entries of the same
    address and time must not share an identifier.
    """
    for entry in ({'time': 1700000000000}, {'time': 1700000000000, 'hash': ZERO_32_BYTES_HEX}):
        assert HyperliquidAPI._entry_unique_id(entry=entry, address=ADDRESS).startswith(f'{ADDRESS}_1700000000000_')  # noqa: E501

    first, second = ({'time': 1700000000000, 'hash': ZERO_32_BYTES_HEX, 'delta': {'type': 'x', 'usdc': amount}} for amount in ('1', '2'))  # noqa: E501
    assert HyperliquidAPI._entry_unique_id(entry=first, address=ADDRESS) != HyperliquidAPI._entry_unique_id(entry=second, address=ADDRESS)  # noqa: E501
    with patch.object(api := HyperliquidAPI(), '_query_list', side_effect=[[first, second], []]):
        assert len({context.group_identifier for page in api._iter_entry_pages(
            query_type='userNonFundingLedgerUpdates',
            address=ADDRESS,
            start_ts=Timestamp(1700000000),
            end_ts=Timestamp(1700000001),
        ) for context in page}) == 2


def test_max_spot_transfer_with_unresolvable_asset_is_skipped(globaldb, caplog) -> None:
    api = HyperliquidAPI()
    address = string_to_evm_address('0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF')
    entry: dict[str, Any] = {
        'time': 1781377469380,
        'hash': '0x1914c6fab113b5861a8e043da5795702031e00e04c16d458bcdd724d70178f70',
        'delta': {
            'type': 'spotTransfer',
            'token': 'MAX',
            'amount': '320121.396989',
            'usdcValue': '0.0',
            'user': '0x207700bd207df757825f9193ef9c648c1c65e06a',
            'destination': '0x3ba6eb0e4327b96ade6d4f3b578724208a590cef',
            'fee': '0.0',
            'nativeTokenFee': '0.0',
            'nonce': 1781377469004,
            'feeToken': '',
        },
    }
    spot_meta = {
        'tokens': [{
            'name': 'MAX',
            'szDecimals': 1,
            'weiDecimals': 6,
            'index': 734,
            'tokenId': '0x6781b92b6ea5d8ed37d275eb201f64af',
            'isCanonical': False,
            'evmContract': None,
            'fullName': '$MAX',
            'deployerTradingFeeShare': '1.0',
        }],
        'universe': [],
    }

    caplog.set_level(logging.WARNING)
    with (
        patch(
            'rotkehlchen.externalapis.hyperliquid.get_asset_id_by_counterparty',
            side_effect=UnknownCounterpartyMapping(symbol='MAX', counterparty='hyperliquid'),
        ),
        patch(
            'rotkehlchen.externalapis.hyperliquid.asset_from_hyperliquid',
            side_effect=UnknownAsset('MAX'),
        ),
        patch.object(api, '_query_dict', return_value=spot_meta),
        patch.object(api, '_query_list', side_effect=[[entry], [], [], []]),
    ):
        events = query_history_events(
            api=api,
            address=address,
            start_ts=Timestamp(1781377469),
            end_ts=Timestamp(1781377470),
        )

    assert events == []
    assert 'asset MAX. Skipping' in caplog.text


def test_iter_entry_pages_pages_forward_through_the_whole_range(caplog) -> None:
    """The API returns the oldest entries of the window, so the next page must start at the
    newest entry of the previous one. Paging backwards from the oldest entry, as before,
    found nothing and kept only the first page."""
    caplog.set_level(logging.WARNING)
    endpoint = FakeHistoryEndpoint(entries=[_fill(tid, tid * 100) for tid in range(1, 8)], cap=3)
    assert _page_tids(HyperliquidAPI(), endpoint) == [[1, 2, 3], [4, 5], [6, 7]]
    assert endpoint.windows == [
        (RANGE_START_MS, 1700000010999),  # covers the whole last second
        (RANGE_START_MS, RANGE_START_MS + 99),  # checks nothing is older than the 1st page
        (RANGE_START_MS + 300, 1700000010999),  # each page starts at the previous newest
        (RANGE_START_MS + 500, 1700000010999),
        (RANGE_START_MS + 700, 1700000010999),  # a page shorter than the cap is the last one
    ]
    assert 'Hyperliquid' not in caplog.text


def test_iter_entry_pages_recovers_a_millisecond_split_between_pages(caplog) -> None:
    """The cap may cut a millisecond in two, so that millisecond is queried again and only
    the entries not seen yet are yielded."""
    caplog.set_level(logging.WARNING)
    endpoint = FakeHistoryEndpoint(
        entries=[_fill(1, 1), _fill(2, 2), _fill(3, 50), _fill(4, 50), _fill(5, 90)],
        cap=3,
    )
    assert _page_tids(HyperliquidAPI(), endpoint) == [[1, 2, 3], [4, 5]]
    assert 'may be missing' not in caplog.text


def test_iter_entry_pages_does_not_rely_on_the_order_inside_a_page() -> None:
    endpoint = FakeHistoryEndpoint(
        entries=[_fill(tid, tid * 100) for tid in range(1, 8)],
        cap=3,
        order='descending',
    )
    assert _page_tids(HyperliquidAPI(), endpoint) == [[3, 2, 1], [5, 4], [7, 6]]


def test_iter_entry_pages_warns_and_moves_on_from_a_full_millisecond(caplog) -> None:
    """A full page in one millisecond can't be paged further since the API has no cursor
    within a millisecond, so move past it and warn that entries may be missing."""
    caplog.set_level(logging.WARNING)
    endpoint = FakeHistoryEndpoint(
        entries=[_fill(1, 50), _fill(2, 50), _fill(3, 50), _fill(4, 60)],
        cap=2,
    )
    assert _page_tids(HyperliquidAPI(), endpoint) == [[1, 2], [4]]
    assert f'full page of entries at {RANGE_START_MS + 50}ms' in caplog.text


def test_iter_entry_pages_does_not_collapse_partial_fills_sharing_oid() -> None:
    """Two partial fills of the same order share `oid` but have distinct `tid`s and occur
    at the same millisecond. They must both be yielded."""
    fills = [
        {'tid': 1, 'oid': 90542681, 'hash': '0xtx', 'time': RANGE_START_MS + 5, 'sz': '4'},
        {'tid': 2, 'oid': 90542681, 'hash': '0xtx', 'time': RANGE_START_MS + 5, 'sz': '6'},
    ]
    assert _page_tids(HyperliquidAPI(), FakeHistoryEndpoint(entries=fills, cap=2)) == [[1, 2]]


def test_iter_entry_pages_includes_the_whole_end_second() -> None:
    """The next queried range starts at the second after `end_ts`, so its last millisecond
    must be covered."""
    endpoint = FakeHistoryEndpoint(entries=[_fill(1, 0), _fill(2, 1999), _fill(3, 2000)], cap=5)
    assert _page_tids(HyperliquidAPI(), endpoint, end_ts=1700000001) == [[1, 2]]


def test_iter_entry_pages_raises_on_an_entry_outside_the_window() -> None:
    """An API ignoring `startTime` would return older entries again, so fail the range."""
    endpoint = FakeHistoryEndpoint(
        entries=[_fill(tid, tid * 100) for tid in range(1, 5)],
        cap=2,
        ignore_start=True,
    )
    with pytest.raises(RemoteError, match='outside of the requested range'):
        _page_tids(HyperliquidAPI(), endpoint)


def test_iter_entry_pages_raises_if_the_api_returns_the_newest_entries() -> None:
    """Paging forward relies on getting the oldest entries of the window. If the API
    returned the newest instead, the history before the first page would be missed."""
    endpoint = FakeHistoryEndpoint(
        entries=[_fill(tid, tid * 100) for tid in range(1, 6)],
        cap=2,
        slice_='newest',
    )
    with pytest.raises(RemoteError, match='did not return the oldest entries'):
        _page_tids(HyperliquidAPI(), endpoint)


@pytest.mark.parametrize('bad_entry', [{'tid': 3, 'time': 'x'}, {'tid': 3}])
def test_iter_entry_pages_raises_on_an_unreadable_time(bad_entry: dict[str, Any]) -> None:
    """An entry with an unreadable time must fail the range. Skipping it could shrink a
    capped page below the cap, so it would look like the last one and the valid entries
    after it would never be queried."""
    entries = [_fill(1, 100), _fill(2, 200), bad_entry]
    with (
        patch.object(api := HyperliquidAPI(), '_query_list', return_value=entries),
        pytest.raises(RemoteError, match='unreadable time'),
    ):
        list(api._iter_entry_pages(
            query_type='userFillsByTime',
            address=ADDRESS,
            start_ts=Timestamp(RANGE_START_MS // 1000),
            end_ts=Timestamp(RANGE_START_MS // 1000 + 10),
        ))


def test_spot_metadata_failure_fails_the_history_query_and_is_retried() -> None:
    """Without spot metadata spot fills can't be resolved, so the query must fail
    instead of skipping them, and the failure must not be cached for the next query.
    The metadata is only queried when there is a spot fill to resolve."""
    api = HyperliquidAPI()
    spot_fill = {'tid': 1, 'time': 1000, 'coin': '@107', 'px': '1', 'sz': '1', 'side': 'B', 'fee': '0', 'feeToken': 'USDC'}  # noqa: E501
    with (
        patch.object(api, '_query_dict', side_effect=RemoteError('spotMeta down')) as spot_meta,
        patch.object(api, '_query_list', side_effect=lambda payload, **_: [spot_fill] if payload['type'] == 'userFillsByTime' else []),  # noqa: E501
    ):
        for _ in range(2):
            with pytest.raises(RemoteError):
                list(api.iter_history_event_batches(
                    address=ADDRESS,
                    start_ts=Timestamp(1),
                    end_ts=Timestamp(2),
                ))

    assert spot_meta.call_count == 2


def test_rate_limited_requests_wait_for_the_rate_limit_window() -> None:
    """The weight limit is per minute, so a rate limited request keeps retrying for that
    long, honoring `Retry-After`, instead of failing a long history query midway."""
    api = HyperliquidAPI()
    limited = MagicMock(status_code=HTTPStatus.TOO_MANY_REQUESTS, headers={})
    with (
        patch.object(api.session, 'post', side_effect=[
            limited,
            MagicMock(status_code=HTTPStatus.TOO_MANY_REQUESTS, headers={'retry-after': '7'}),
            *[limited] * 4,
            MagicMock(status_code=HTTPStatus.OK, json=MagicMock(return_value=[])),
        ]),
        patch('rotkehlchen.externalapis.hyperliquid.cancellable_sleep') as sleep,
    ):
        assert api._post_info({'type': 'userFunding'}, wait_for_rate_limit=True) == []

    assert [call.args[0] for call in sleep.call_args_list] == [1, 7, 4, 8, 16, 32]

    with (
        patch.object(api.session, 'post', return_value=limited),
        patch('rotkehlchen.externalapis.hyperliquid.cancellable_sleep') as sleep,
        pytest.raises(RemoteError, match='after waiting 63 seconds'),
    ):
        api._post_info({'type': 'userFunding'}, wait_for_rate_limit=True)

    assert sum(call.args[0] for call in sleep.call_args_list) == 63

    with (
        patch.object(api.session, 'post', return_value=limited),
        patch('rotkehlchen.externalapis.hyperliquid.cancellable_sleep') as sleep,
        pytest.raises(RemoteError, match='after waiting 15 seconds'),
    ):
        api._post_info({'type': 'userFunding'})  # balance queries don't wait for the window

    assert sum(call.args[0] for call in sleep.call_args_list) == 15


def test_same_funding_payment_of_two_addresses_is_saved_for_both(database: DBHandler) -> None:
    """Every user gets funding at the same times, so the same coin's payment of a main
    account and its subaccount must not share a group identifier and get dropped."""
    entry = {'time': 1762300800000, 'hash': '0x' + '0' * 64, 'delta': {'type': 'funding', 'coin': 'BTC', 'usdc': '1.5'}}  # noqa: E501
    api, events = HyperliquidAPI(), list[HistoryBaseEntry]()
    for address in (ADDRESS, SUBACCOUNT):
        with patch.object(api, '_query_list', side_effect=[[entry], []]):
            events.extend(event for page in api._iter_entry_pages(
                query_type='userFunding',
                address=address,
                start_ts=Timestamp(1762300800),
                end_ts=Timestamp(1762300801),
            ) for event in api._create_funding_events(address=address, contexts=page))

    with database.user_write() as write_cursor:
        assert DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=events) == 2  # noqa: E501

    with database.conn.read_ctx() as cursor:
        assert {row[0] for row in cursor.execute('SELECT location_label FROM history_events')} == {ADDRESS, SUBACCOUNT}  # noqa: E501
