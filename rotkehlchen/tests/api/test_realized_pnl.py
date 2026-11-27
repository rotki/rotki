from typing import TYPE_CHECKING, Any
from unittest.mock import ANY, patch

import pytest
import requests

from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USD
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import (
    LOCATION_ETHEREUM,
    LOCATION_KRAKEN,
    LOCATION_OPTIMISM,
)
from rotkehlchen.tasks.cost_basis import process_cost_basis
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_sync_response_with_result
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Price, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.locations.types import LocationIdentifier
    from rotkehlchen.types import ChecksumEvmAddress

pytestmark = pytest.mark.accounting_update

JAN_10_2023: Timestamp = Timestamp(1673308800)
JAN_12_2023: Timestamp = Timestamp(1673481600)  # same week as the 10th
FEB_20_2024: Timestamp = Timestamp(1708387200)
DEC_31_2024: Timestamp = Timestamp(1735603200)  # ISO week 2025-W01
JAN_01_2025: Timestamp = Timestamp(1735689600)  # ISO week 2025-W01


def _event(
        timestamp: Timestamp,
        event_type: HistoryEventType,
        asset: Asset = A_ETH,
        location: LocationIdentifier = LOCATION_ETHEREUM,
        location_label: ChecksumEvmAddress = TEST_ADDR1,
) -> EvmEvent:
    return EvmEvent(
        tx_ref=make_evm_tx_hash(),
        sequence_index=0,
        timestamp=TimestampMS(timestamp * 1000),
        location=location,
        event_type=event_type,
        event_subtype=HistoryEventSubType.NONE,
        asset=asset,
        amount=FVal(1),
        location_label=location_label,
    )


@pytest.fixture(name='materialized_pnl')
def fixture_materialized_pnl(rotkehlchen_api_server: APIServer) -> None:
    """Three spends of 1 unit bought at 100, realizing 900, 1900 and 2900.

    ETH on ethereum from one address in January 2023, BTC on ethereum from another address two
    days later, and ETH on optimism in February 2024.
    """
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    DBAccountingRules(database).add_accounting_rule(
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        counterparty=None,
        rule=BaseEventSettings(
            taxable=True,
            count_entire_amount_spend=False,
            count_cost_basis_pnl=True,
        ),
        links={},
    )
    spends = (
        (JAN_10_2023, A_ETH, LOCATION_ETHEREUM, TEST_ADDR1),
        (JAN_12_2023, A_BTC, LOCATION_ETHEREUM, TEST_ADDR2),
        (FEB_20_2024, A_ETH, LOCATION_OPTIMISM, TEST_ADDR1),
    )
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(
                timestamp=Timestamp(timestamp - offset),
                event_type=event_type,
                asset=asset,
                location=location,
                location_label=location_label,
            )
            for timestamp, asset, location, location_label in spends
            for offset, event_type in ((100, HistoryEventType.RECEIVE), (0, HistoryEventType.SPEND))  # noqa: E501
        ])

    prices = {JAN_10_2023: 1000, JAN_12_2023: 2000, FEB_20_2024: 3000}

    def query_historical_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return Price(FVal(prices.get(timestamp, 100)))

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_historical_price
        assert process_cost_basis(database, database.msg_aggregator) is True


def _query(server: APIServer, **json: Any) -> dict[str, Any]:
    return assert_proper_sync_response_with_result(requests.post(
        api_url_for(server, 'realizedpnlresource'),
        json=json,
    ))


def _group(
        key: str | None,
        pnl: int,
        events: int = 1,
        unpriced_events: int = 0,
        taxfree_pnl: int = 0,
) -> dict[str, Any]:
    return {
        'group_key': key,
        'realized_pnl': str(pnl),
        'taxfree_pnl': str(taxfree_pnl),
        'basis_removed': str(100 * events),
        'num_events': events,
        'num_unpriced_events': unpriced_events,
    }


def _readiness(
        *,
        stale: bool = False,
        open_issues_by_kind: dict[str, int] | None = None,
        num_unpriced_events: int = 0,
        num_unruled_events: int = 0,
        evaluated_through_ts: Any = ANY,
) -> dict[str, Any]:
    by_kind = {} if open_issues_by_kind is None else open_issues_by_kind
    open_count = sum(by_kind.values())
    return {
        'ready': (not stale) and open_count == 0,
        'stale': stale,
        'open_issues_count': open_count,
        'open_issues_by_kind': by_kind,
        'num_unpriced_events': num_unpriced_events,
        'num_unruled_events': num_unruled_events,
        'evaluated_through_ts': evaluated_through_ts,
    }


@pytest.mark.parametrize(('group_by', 'breakdown'), [
    (None, [_group(None, 5700, 3)]),
    ('asset', [_group('BTC', 1900), _group('ETH', 3800, 2)]),
    ('location', [_group('ethereum', 2800, 2), _group('optimism', 2900)]),
    ('location_label', [_group(TEST_ADDR2, 1900), _group(TEST_ADDR1, 3800, 2)]),
    ('protocol', [_group(None, 5700, 3)]),
    ('day', [_group('2023-01-10', 900), _group('2023-01-12', 1900), _group('2024-02-20', 2900)]),
    ('week', [_group('2023-W02', 2800, 2), _group('2024-W08', 2900)]),
    ('month', [_group('2023-01', 2800, 2), _group('2024-02', 2900)]),
    ('year', [_group('2023', 2800, 2), _group('2024', 2900)]),
])
@pytest.mark.usefixtures('materialized_pnl')
def test_realized_pnl_is_broken_down_by_group(
        rotkehlchen_api_server: APIServer,
        group_by: str | None,
        breakdown: list[dict[str, Any]],
) -> None:
    assert _query(rotkehlchen_api_server, group_by=group_by) == {
        'total_realized_pnl': '5700',
        'total_taxfree_pnl': '0',
        'num_unpriced_events': 0,
        'num_unruled_events': 3,
        'breakdown': sorted(breakdown, key=lambda group: group['group_key'] or ''),
        'stale': False,
        'method': 'fifo',
        'report_readiness': _readiness(num_unruled_events=3),
    }


@pytest.mark.parametrize(('filters', 'total'), [
    ({'from_timestamp': JAN_12_2023, 'to_timestamp': FEB_20_2024 - 1}, '1900'),
    ({'asset': 'ETH'}, '3800'),
    ({'location': 'optimism'}, '2900'),
    ({'location_labels': [TEST_ADDR1], 'to_timestamp': JAN_12_2023}, '900'),
    ({'event_types': ['receive']}, '0'),  # non-taxable receives realize nothing
    ({'asset': 'ETH', 'location_labels': [TEST_ADDR2]}, '0'),
    ({'state_markers': ['customized']}, '0'),
    ({'state_markers': ['matched']}, '0'),
    ({'addresses': ['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']}, '0'),
])
@pytest.mark.usefixtures('materialized_pnl')
def test_realized_pnl_only_counts_the_events_matching_the_filter(
        rotkehlchen_api_server: APIServer,
        filters: dict[str, Any],
        total: str,
) -> None:
    result = _query(rotkehlchen_api_server, **filters)
    assert result['total_realized_pnl'] == total
    assert result['total_taxfree_pnl'] == '0'
    assert result['num_unpriced_events'] == 0
    assert (result['breakdown'] == []) is (total == '0')


@pytest.mark.usefixtures('materialized_pnl')
def test_realized_pnl_filters_by_identifiers(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with database.conn.read_ctx() as cursor:
        _, optimism_spend_id = (row[0] for row in cursor.execute(
            'SELECT identifier FROM history_events WHERE location=? ORDER BY timestamp',
            (LOCATION_OPTIMISM,),
        ))

    assert _query(rotkehlchen_api_server, identifiers=[optimism_spend_id]) == {
        'total_realized_pnl': '2900',
        'total_taxfree_pnl': '0',
        'num_unpriced_events': 0,
        'num_unruled_events': 0,
        'breakdown': [_group(None, 2900, events=1)],
        'stale': False,
        'method': 'fifo',
        'report_readiness': _readiness(),
    }


def test_realized_pnl_is_stale_until_the_cost_basis_is_processed(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    empty = {
        'total_realized_pnl': '0',
        'total_taxfree_pnl': '0',
        'num_unpriced_events': 0,
        'num_unruled_events': 0,
        'breakdown': [],
        'method': 'fifo',
    }
    assert _query(rotkehlchen_api_server) == empty | {
        'stale': True,
        'report_readiness': _readiness(stale=True),
    }  # never processed

    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _query(rotkehlchen_api_server) == empty | {
        'stale': False,
        'report_readiness': _readiness(stale=False),
    }

    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO key_value_cache(name, value) VALUES (?, ?)',
            (DBCacheStatic.STALE_COST_BASIS_FROM_TS.value, '5'),
        )
    assert _query(rotkehlchen_api_server) == empty | {
        'stale': True,
        'report_readiness': _readiness(stale=True),
    }


@pytest.mark.usefixtures('materialized_pnl')
def test_events_cost_basis_shows_the_lots_behind_each_event(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with database.conn.read_ctx() as cursor:
        acquired, spent = (row[0] for row in cursor.execute(
            'SELECT identifier FROM history_events WHERE location=? AND asset=? '
            'ORDER BY timestamp',
            (LOCATION_OPTIMISM, A_ETH.identifier),
        ))
        group_identifier = cursor.execute(
            'SELECT group_identifier FROM history_events WHERE identifier=?',
            (acquired,),
        ).fetchone()[0]

    bucket = {
        'location': 'optimism',
        'location_label': TEST_ADDR1,
        'protocol': None,
        'asset': 'ETH',
        'method': 'fifo',
    }
    acquired_entry = [bucket | {
        'direction': 'receive',
        'lot_ids': [str(acquired)],
        'basis_per_unit': '100',
        'basis_source': 'price_oracle',
    }]
    assert assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'eventscostbasisresource'),
        json={'event_identifiers': [acquired, spent, 999]},  # 999 does not exist
    )) == {
        'entries': {
            str(acquired): acquired_entry,
            str(spent): [bucket | {
                'direction': 'spend',
                'lots': [{
                    'lot_id': str(acquired),
                    'acquired_at': FEB_20_2024 - 100,
                    'amount': '1',
                    'basis_per_unit': '100',
                    'taxable': True,
                    'acquisition': {
                        'identifier': acquired,
                        'group_identifier': group_identifier,
                        'location': 'optimism',
                        'location_label': TEST_ADDR1,
                        'timestamp': (FEB_20_2024 - 100) * 1000,
                    },
                }],
                'proceeds': '3000',
                'realized_pnl': '2900',
                'taxfree_pnl': '0',
                'basis_removed': '100',
                'basis_remaining': '0',
            }],
        },
        'stale': [],
        'method': 'fifo',
    }

    # Only events at or after the stale marker are reported as stale and hidden from entries.
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            value=str(FEB_20_2024 * 1000),
        )
    assert assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'eventscostbasisresource'),
        json={'event_identifiers': [acquired, spent, 999]},
    )) == {
        'entries': {str(acquired): acquired_entry},
        'stale': [spent],
        'method': 'fifo',
    }

    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            value='0',
        )
    assert assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'eventscostbasisresource'),
        json={'event_identifiers': [acquired, spent, 999]},
    )) == {
        'entries': {},
        'stale': [acquired, spent],
        'method': 'fifo',
    }


def test_unpriced_spend_returns_null_pnl_and_does_not_fail_summary(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    DBAccountingRules(database).add_accounting_rule(
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        counterparty=None,
        rule=BaseEventSettings(
            taxable=True,
            count_entire_amount_spend=False,
            count_cost_basis_pnl=True,
        ),
        links={},
    )
    with database.user_write() as write_cursor:
        acquired = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=_event(timestamp=Timestamp(JAN_10_2023 - 100), event_type=HistoryEventType.RECEIVE),  # noqa: E501
        )
        spent = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=_event(timestamp=JAN_10_2023, event_type=HistoryEventType.SPEND),
        )
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(timestamp=Timestamp(JAN_12_2023 - 100), event_type=HistoryEventType.RECEIVE, asset=A_BTC),  # noqa: E501
            _event(timestamp=JAN_12_2023, event_type=HistoryEventType.SPEND, asset=A_BTC),
        ])
    assert acquired is not None and spent is not None

    def query_historical_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if timestamp == JAN_10_2023:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )
        if timestamp == JAN_12_2023:
            return Price(FVal(2000))
        return Price(FVal(100))

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_historical_price
        assert process_cost_basis(database, database.msg_aggregator) is True

    assert _query(rotkehlchen_api_server, group_by='asset') == {
        'total_realized_pnl': '1900',
        'total_taxfree_pnl': '0',
        'num_unpriced_events': 1,
        'num_unruled_events': 2,
        'breakdown': [
            _group('BTC', 1900, events=1, unpriced_events=0),
            _group('ETH', 0, events=1, unpriced_events=1),
        ],
        'stale': False,
        'method': 'fifo',
        'report_readiness': _readiness(
            open_issues_by_kind={IssueKind.MISSING_PRICE.value: 1},
            num_unpriced_events=1,
            num_unruled_events=2,
        ),
    }

    cost_basis = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'eventscostbasisresource'),
        json={'event_identifiers': [spent]},
    ))
    assert cost_basis['stale'] == []
    spend_entry = cost_basis['entries'][str(spent)][0]
    assert spend_entry['proceeds'] is None
    assert spend_entry['realized_pnl'] is None
    assert spend_entry['taxfree_pnl'] is None
    assert spend_entry['basis_removed'] == '100'
    assert spend_entry['basis_remaining'] == '0'


def test_unpriced_taxable_receives_are_counted_as_unpriced(
        rotkehlchen_api_server: APIServer,
) -> None:
    """Unpriced taxable crypto and fiat receives store null PnL and increment unpriced counts,
    while unpriced non-taxable receives are excluded from PnL totals and unpriced counts."""
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    rules_db = DBAccountingRules(database)
    rules_db.add_accounting_rule(
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        counterparty=None,
        rule=BaseEventSettings(
            taxable=False,
            count_entire_amount_spend=False,
            count_cost_basis_pnl=False,
        ),
        links={},
    )
    for subtype in (HistoryEventSubType.AIRDROP, HistoryEventSubType.INTEREST):
        rules_db.add_accounting_rule(
            event_type=HistoryEventType.RECEIVE,
            event_subtype=subtype,
            counterparty=None,
            rule=BaseEventSettings(
                taxable=True,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
            ),
            links={},
        )

    events_db = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        nontaxable_eth = events_db.add_history_event(
            write_cursor=write_cursor,
            event=_event(timestamp=JAN_10_2023, event_type=HistoryEventType.RECEIVE),
        )
        unpriced_airdrop = events_db.add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(JAN_10_2023 * 1000),
                location=LOCATION_ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.AIRDROP,
                asset=A_ETH,
                amount=FVal(1),
                location_label=TEST_ADDR1,
            ),
        )
        priced_airdrop = events_db.add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(JAN_12_2023 * 1000),
                location=LOCATION_ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.AIRDROP,
                asset=A_BTC,
                amount=FVal(1),
                location_label=TEST_ADDR1,
            ),
        )
        unpriced_fiat_interest = events_db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                timestamp=TimestampMS(FEB_20_2024 * 1000),
                location=LOCATION_KRAKEN,
                location_label='kraken',
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.INTEREST,
                asset=A_USD,
                amount=FVal(100),
                group_identifier='usd_interest_unpriced',
                sequence_index=0,
            ),
        )
    assert nontaxable_eth is not None
    assert unpriced_airdrop is not None
    assert priced_airdrop is not None
    assert unpriced_fiat_interest is not None

    def query_historical_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if from_asset == A_BTC and timestamp == JAN_12_2023:
            return Price(FVal(2000))
        raise NoPriceForGivenTimestamp(from_asset=from_asset, to_asset=to_asset, time=timestamp)

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_historical_price
        assert process_cost_basis(database, database.msg_aggregator) is True

    with database.conn.read_ctx() as cursor:
        rows = {
            row[0]: row[1:]
            for row in cursor.execute(
                'SELECT event_identifier, basis_source, realized_pnl, taxfree_pnl, is_taxable '
                'FROM event_cost_basis',
            )
        }
    assert rows == {
        nontaxable_eth: ('zero_cost', None, None, 0),
        unpriced_airdrop: ('zero_cost', None, None, 1),
        priced_airdrop: ('price_oracle', '2000', '0', 1),
        unpriced_fiat_interest: ('zero_cost', None, None, 1),
    }

    assert _query(rotkehlchen_api_server, group_by='asset') == {
        'total_realized_pnl': '2000',
        'total_taxfree_pnl': '0',
        'num_unpriced_events': 2,
        'num_unruled_events': 0,
        'breakdown': [
            {
                'group_key': 'BTC',
                'realized_pnl': '2000',
                'taxfree_pnl': '0',
                'basis_removed': '0',
                'num_events': 1,
                'num_unpriced_events': 0,
            },
            {
                'group_key': 'ETH',
                'realized_pnl': '0',
                'taxfree_pnl': '0',
                'basis_removed': '0',
                'num_events': 1,
                'num_unpriced_events': 1,
            },
            {
                'group_key': 'USD',
                'realized_pnl': '0',
                'taxfree_pnl': '0',
                'basis_removed': '0',
                'num_events': 1,
                'num_unpriced_events': 1,
            },
        ],
        'stale': False,
        'method': 'fifo',
        'report_readiness': _readiness(
            open_issues_by_kind={IssueKind.MISSING_PRICE.value: 3},
            num_unpriced_events=2,
        ),
    }


def test_realized_pnl_groups_year_boundary_week_together(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    DBAccountingRules(database).add_accounting_rule(
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        counterparty=None,
        rule=BaseEventSettings(
            taxable=True,
            count_entire_amount_spend=False,
            count_cost_basis_pnl=True,
        ),
        links={},
    )
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(write_cursor=write_cursor, history=[
            _event(timestamp=Timestamp(ts - offset), event_type=event_type)
            for ts in (DEC_31_2024, JAN_01_2025)
            for offset, event_type in ((100, HistoryEventType.RECEIVE), (0, HistoryEventType.SPEND))  # noqa: E501
        ])

    prices = {DEC_31_2024: 1000, JAN_01_2025: 2000}

    def query_historical_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return Price(FVal(prices.get(timestamp, 100)))

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_historical_price
        assert process_cost_basis(database, database.msg_aggregator) is True

    assert _query(rotkehlchen_api_server, group_by='week') == {
        'total_realized_pnl': '2800',
        'total_taxfree_pnl': '0',
        'num_unpriced_events': 0,
        'num_unruled_events': 2,
        'breakdown': [_group('2025-W01', 2800, events=2)],
        'stale': False,
        'method': 'fifo',
        'report_readiness': _readiness(num_unruled_events=2),
    }


@pytest.mark.usefixtures('materialized_pnl')
def test_realized_pnl_report_readiness_window_and_manual_confirmation(
        rotkehlchen_api_server: APIServer,
) -> None:
    """Open issues at or before to_timestamp (including pre-window ones) block readiness,
    issues after to_timestamp do not, manual confirmations unblock readiness, and unruled
    events are reported without blocking."""
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    manager = DataIssuesManager(database)

    # Pre-window open issue (before JAN_12_2023)
    pre_window_issue_id = manager.write_issue(
        IssueKind.MISSING_COST_BASIS,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
        protocol=None,
        asset='ETH',
        payload={
            'event_identifier': 500,
            'group_identifier': 'pre-window-grp',
            'requested_amount': '1',
            'covered_amount': '0',
            'uncovered_amount': '1',
            'fallback_basis': '0',
        },
        ts_start=JAN_10_2023 * 1000,
        ts_end=JAN_10_2023 * 1000,
    )
    # Post-window open issue (after JAN_12_2023, inside 2024)
    manager.write_issue(
        IssueKind.MISSING_PRICE,
        location=LOCATION_OPTIMISM,
        location_label=TEST_ADDR1,
        protocol=None,
        asset='ETH',
        payload={
            'event_identifier': 501,
            'group_identifier': 'post-window-grp',
            'to_asset': 'USD',
            'amount': '1',
            'direction': 'spend',
        },
        ts_start=FEB_20_2024 * 1000,
        ts_end=FEB_20_2024 * 1000,
    )

    # Querying [JAN_12_2023, JAN_12_2023]: pre-window issue blocks, post-window does NOT
    in_2023 = _query(
        rotkehlchen_api_server,
        from_timestamp=JAN_12_2023,
        to_timestamp=JAN_12_2023,
    )
    assert in_2023['report_readiness'] == _readiness(
        open_issues_by_kind={IssueKind.MISSING_COST_BASIS.value: 1},
        num_unruled_events=0,
        evaluated_through_ts=JAN_12_2023 * 1000,
    )
    assert in_2023['report_readiness']['ready'] is False

    # Manually confirming the pre-window issue unblocks the 2023 window even with unruled events
    assert_proper_sync_response_with_result(requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'dataissueresolvemanuallyresource',
            issue_id=pre_window_issue_id,
        ),
        json={'disposition': 'confirm_zero_basis', 'note': 'accepted'},
    ))
    in_2023_after = _query(
        rotkehlchen_api_server,
        from_timestamp=JAN_10_2023 - 200,
        to_timestamp=JAN_12_2023,
    )
    assert in_2023_after['num_unruled_events'] == 2
    assert in_2023_after['report_readiness'] == _readiness(
        num_unruled_events=2,
        evaluated_through_ts=JAN_12_2023 * 1000,
    )
    assert in_2023_after['report_readiness']['ready'] is True

    # Unbounded query still sees the post-window 2024 issue
    unbounded = _query(rotkehlchen_api_server)
    assert unbounded['report_readiness']['ready'] is False
    assert unbounded['report_readiness']['open_issues_by_kind'] == {
        IssueKind.MISSING_PRICE.value: 1,
    }


@pytest.mark.usefixtures('materialized_pnl')
def test_events_cost_basis_serves_completed_prefix_of_unfinished_pass(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with database.conn.read_ctx() as cursor:
        acquired, spent = (row[0] for row in cursor.execute(
            'SELECT identifier FROM history_events WHERE location=? AND asset=? '
            'ORDER BY timestamp',
            (LOCATION_OPTIMISM, A_ETH.identifier),
        ))

    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            value='0',
        )
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
            value='42',
        )
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.COST_BASIS_PASS_PROCESSED_TS,
            value=str(FEB_20_2024 * 1000),
        )
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.COST_BASIS_PASS_MODIFICATION_TS,
            value='42',
        )

    result = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'eventscostbasisresource'),
        json={'event_identifiers': [acquired, spent]},
    ))
    assert list(result['entries']) == [str(acquired)]
    assert result['stale'] == [spent]

    # Once a newer modification happens, the unfinished pass progress is ignored.
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
            value='43',
        )
    invalidated = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'eventscostbasisresource'),
        json={'event_identifiers': [acquired, spent]},
    ))
    assert invalidated['entries'] == {}
    assert invalidated['stale'] == [acquired, spent]
