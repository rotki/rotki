from typing import TYPE_CHECKING

from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.filtering import DataIssuesFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.locations import DBLocations
from rotkehlchen.history.data_issues.constants import IssueKind
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import (
    LOCATION_BANKS,
    LOCATION_BLOCKCHAIN,
    LOCATION_ETHEREUM,
    LOCATION_EVM_CHAINS,
    LOCATION_EXCHANGES,
    LOCATION_EXTERNAL,
    LOCATION_KRAKEN,
    LOCATION_OPTIMISM,
    LOCATION_QONTO,
    LOCATION_TOTAL,
)
from rotkehlchen.locations.types import LocationIdentifier, LocationScope
from rotkehlchen.types import TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _add_events_at(database: DBHandler, locations: dict[str, LocationIdentifier]) -> None:
    """Add one event per location, using the given name as its group identifier"""
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[HistoryEvent(
                group_identifier=name,
                sequence_index=0,
                timestamp=TimestampMS(1700000000000 + idx),
                location=location,
                asset=A_ETH,
                amount=ONE,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
            ) for idx, (name, location) in enumerate(locations.items())],
        )


def test_history_events_location_scopes(database: DBHandler) -> None:
    """Exact matches only the direct location, subtree also every descendant, broad parent
    locations hold their own events, and exclusions expand the same way"""
    db_locations = DBLocations()
    with database.user_write() as write_cursor:
        ing = db_locations.add_custom(write_cursor, name='ING', parent_identifier=LOCATION_BANKS)
        savings = db_locations.add_custom(write_cursor, name='Savings', parent_identifier=ing.identifier)  # noqa: E501

    _add_events_at(database, {
        'ethereum': LOCATION_ETHEREUM,
        'optimism': LOCATION_OPTIMISM,
        'blockchain': LOCATION_BLOCKCHAIN,  # a broad bucket for an unknown chain
        'kraken': LOCATION_KRAKEN,
        'qonto': LOCATION_QONTO,
        'banks': LOCATION_BANKS,
        'ing': ing.identifier,
        'savings': savings.identifier,
        'external': LOCATION_EXTERNAL,
    })

    def query(
            location: LocationIdentifier | None,
            scope: LocationScope,
            excluded: list[LocationIdentifier] | None = None,
    ) -> set[str]:
        with database.conn.read_ctx() as cursor:
            return {x.group_identifier for x in DBHistoryEvents(database).get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    location=location,
                    location_scope=scope,
                    excluded_locations=excluded,
                ),
                entries_limit=None,
            )}

    everything = {'ethereum', 'optimism', 'blockchain', 'kraken', 'qonto', 'banks', 'ing', 'savings', 'external'}  # noqa: E501
    for location, scope, expected in (
        (LOCATION_TOTAL, LocationScope.EXACT, set()),
        (LOCATION_TOTAL, LocationScope.SUBTREE, everything),
        (LOCATION_BLOCKCHAIN, LocationScope.EXACT, {'blockchain'}),
        (LOCATION_BLOCKCHAIN, LocationScope.SUBTREE, {'ethereum', 'optimism', 'blockchain'}),
        (LOCATION_EVM_CHAINS, LocationScope.EXACT, set()),
        (LOCATION_EVM_CHAINS, LocationScope.SUBTREE, {'ethereum', 'optimism'}),
        (LOCATION_ETHEREUM, LocationScope.EXACT, {'ethereum'}),
        (LOCATION_ETHEREUM, LocationScope.SUBTREE, {'ethereum'}),
        (LOCATION_EXCHANGES, LocationScope.SUBTREE, {'kraken'}),
        (LOCATION_BANKS, LocationScope.EXACT, {'banks'}),
        (LOCATION_BANKS, LocationScope.SUBTREE, {'qonto', 'banks', 'ing', 'savings'}),
        (ing.identifier, LocationScope.EXACT, {'ing'}),
        (ing.identifier, LocationScope.SUBTREE, {'ing', 'savings'}),
    ):
        assert query(location, scope) == expected, f'{location} {scope}'

    assert query(None, LocationScope.SUBTREE, excluded=[LOCATION_BANKS, LOCATION_EVM_CHAINS]) == {
        'blockchain', 'kraken', 'external',
    }
    assert query(None, LocationScope.EXACT, excluded=[LOCATION_BANKS]) == everything - {'banks'}
    assert query(LOCATION_TOTAL, LocationScope.SUBTREE, excluded=[LOCATION_TOTAL]) == set()

    # archiving and moving keep the data queryable, following the new tree
    with database.user_write() as write_cursor:
        db_locations.edit_custom(write_cursor, savings.identifier, parent_identifier=LOCATION_EXTERNAL, is_active=False)  # noqa: E501

    assert query(ing.identifier, LocationScope.SUBTREE) == {'ing'}
    assert query(LOCATION_EXTERNAL, LocationScope.SUBTREE) == {'external', 'savings'}
    assert query(savings.identifier, LocationScope.EXACT) == {'savings'}


def test_data_issues_location_scopes(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    for location in (LOCATION_ETHEREUM, LOCATION_OPTIMISM, LOCATION_KRAKEN):
        manager.write_issue(
            kind=IssueKind.NEGATIVE_BALANCE,
            location=location,
            location_label=None,
            protocol=None,
            asset=A_ETH.identifier,
            payload={
                'event_identifier': 1,
                'in_memory_negative_amount': '-1',
                'derived_balance_before_event': '1',
            },
            ts_start=1000,
            ts_end=1000,
        )

    for location, scope, expected in (
        (LOCATION_EVM_CHAINS, LocationScope.EXACT, set()),
        (LOCATION_EVM_CHAINS, LocationScope.SUBTREE, {LOCATION_ETHEREUM, LOCATION_OPTIMISM}),
        (LOCATION_OPTIMISM, LocationScope.EXACT, {LOCATION_OPTIMISM}),
        (LOCATION_TOTAL, LocationScope.SUBTREE, {LOCATION_ETHEREUM, LOCATION_OPTIMISM, LOCATION_KRAKEN}),  # noqa: E501
    ):
        filter_query = DataIssuesFilterQuery.make(location=location, location_scope=scope)
        assert {x.location for x in manager.list_issues(filter_query)} == expected
        assert manager.count_issues(filter_query) == len(expected)


def test_subtree_filter_uses_location_index(database: DBHandler) -> None:
    """The subtree is resolved once and then probes the history events location index,
    instead of joining the location tree against every event"""
    filter_str, bindings = HistoryEventFilterQuery.make(
        location=LOCATION_EVM_CHAINS,
        location_scope=LocationScope.SUBTREE,
    ).prepare(with_pagination=False, with_order=False)
    with database.conn.read_ctx() as cursor:
        plan = ' | '.join(row[3] for row in cursor.execute(
            f'EXPLAIN QUERY PLAN SELECT identifier FROM history_events {filter_str}',
            bindings,
        ))
    assert 'INDEX idx_history_events_location (location=?)' in plan
    assert 'SCAN history_events' not in plan
