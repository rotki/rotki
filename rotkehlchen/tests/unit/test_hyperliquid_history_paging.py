"""Page Hyperliquid Core history over real API responses.

The unit tests of the pager use a fake endpoint built from what the API was observed to do:
return the oldest entries of the inclusive `startTime`/`endTime` window, in ascending order.
These tests check that assumption against recorded responses. Each range holds more than one
page of a busy account, so a pager that misses the second page fails them.

The expected counts were not taken from the pager. They come from querying each range in
windows small enough to never reach the page cap, and joining the entries by their identity.
"""
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.externalapis.hyperliquid import HistoryQueryType, HyperliquidAPI
from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.hyperliquid import EntryContext
    from rotkehlchen.types import ChecksumEvmAddress

HLP_VAULT = string_to_evm_address('0xdfc24b077bc1425AD1DEA75bCB6f8158E10Df303')
TRADER = string_to_evm_address('0xa62b923A112D50D03e1e096bBD53422490DAC104')


def _query_pages(
        query_type: HistoryQueryType,
        address: ChecksumEvmAddress,
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> list[list[EntryContext]]:
    return list(HyperliquidAPI()._iter_entry_pages(
        query_type=query_type,
        address=address,
        start_ts=start_ts,
        end_ts=end_ts,
    ))


def _assert_complete(
        pages: list[list[EntryContext]],
        count: int,
        first_ms: int,
        last_ms: int,
) -> None:
    """Check that the pages hold every entry of the range once, from its first to its last."""
    contexts = [context for page in pages for context in page]
    assert len(pages) > 1
    assert len(contexts) == len({context.unique_id for context in contexts}) == count
    assert min(context.timestamp for context in contexts) == first_ms
    assert max(context.timestamp for context in contexts) == last_ms


@pytest.mark.vcr(match_on=['uri', 'method', 'body'])
def test_ledger_updates_are_paged_past_the_first_page() -> None:
    """The ledger of the HLP vault returns 2000 entries per page. Paging backwards from the
    oldest entry of the first page, as before, kept only the first 2000 of the 2900."""
    _assert_complete(
        pages=_query_pages(
            query_type='userNonFundingLedgerUpdates',
            address=HLP_VAULT,
            start_ts=Timestamp(1683243596),  # 2023-05-04, the vault's first entry
            end_ts=Timestamp(1686500000),
        ),
        count=2900,
        first_ms=1683243596849,
        last_ms=1686498292321,
    )


@pytest.mark.vcr(match_on=['uri', 'method', 'body'])
def test_fills_are_paged_past_the_first_page() -> None:
    """Fills come 2000 per page and many share a millisecond, so the page boundary falls
    inside a millisecond that has to be queried again without losing or repeating fills."""
    _assert_complete(
        pages=_query_pages(
            query_type='userFillsByTime',
            address=TRADER,
            start_ts=Timestamp(1791444483),
            end_ts=Timestamp(1791466083),
        ),
        count=3731,
        first_ms=1791444492049,
        last_ms=1791466054419,
    )


@pytest.mark.vcr(match_on=['uri', 'method', 'body'])
def test_funding_is_paged_and_every_payment_is_saved(database: DBHandler) -> None:
    """Funding comes 500 per page. All funding entries have the zero hash, and using it as
    their identity gave every payment the same group identifier, so only the first one was
    saved. Every payment must be saved, including payments for several coins at once."""
    _assert_complete(
        pages=(pages := _query_pages(
            query_type='userFunding',
            address=TRADER,
            start_ts=Timestamp(1762300800),
            end_ts=Timestamp(1791468000),
        )),
        count=759,
        first_ms=1762300800000,
        last_ms=1791468000022,
    )
    events = [event for page in pages for event in HyperliquidAPI()._create_funding_events(
        address=TRADER,
        contexts=page,
    )]
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=events)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE location=?',
            (Location.HYPERLIQUID.serialize_for_db(),),
        ).fetchone()[0] == len(events) > 700
