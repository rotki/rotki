from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM, LOCATION_OPTIMISM
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


def _group(key: str | None, pnl: int, events: int = 1) -> dict[str, Any]:
    return {
        'group_key': key,
        'realized_pnl': str(pnl),
        'basis_removed': str(100 * events),
        'num_events': events,
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
        'breakdown': sorted(breakdown, key=lambda group: group['group_key'] or ''),
        'stale': False,
        'method': 'fifo',
    }


@pytest.mark.parametrize(('filters', 'total'), [
    ({'from_timestamp': JAN_12_2023, 'to_timestamp': FEB_20_2024 - 1}, '1900'),
    ({'asset': 'ETH'}, '3800'),
    ({'location': 'optimism'}, '2900'),
    ({'location_labels': [TEST_ADDR1], 'to_timestamp': JAN_12_2023}, '900'),
    ({'event_types': ['receive']}, '0'),  # only spends realize anything
    ({'asset': 'ETH', 'location_labels': [TEST_ADDR2]}, '0'),
])
@pytest.mark.usefixtures('materialized_pnl')
def test_realized_pnl_only_counts_the_events_matching_the_filter(
        rotkehlchen_api_server: APIServer,
        filters: dict[str, Any],
        total: str,
) -> None:
    result = _query(rotkehlchen_api_server, **filters)
    assert result['total_realized_pnl'] == total
    assert (result['breakdown'] == []) is (total == '0')


def test_realized_pnl_is_stale_until_the_cost_basis_is_processed(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    empty = {'total_realized_pnl': '0', 'breakdown': [], 'method': 'fifo'}
    assert _query(rotkehlchen_api_server) == empty | {'stale': True}  # never processed

    assert process_cost_basis(database, database.msg_aggregator) is True
    assert _query(rotkehlchen_api_server) == empty | {'stale': False}

    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO key_value_cache(name, value) VALUES (?, ?)',
            (DBCacheStatic.STALE_COST_BASIS_FROM_TS.value, '5'),
        )
    assert _query(rotkehlchen_api_server) == empty | {'stale': True}
