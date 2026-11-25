"""End-to-end API & automated agent triage loop for PnL data issues.

Exercises the closed loop across all 4 PnL IssueKinds:
detect in process_cost_basis -> query realized PnL readiness (ready=False) -> inspect
data_issues suggested_actions -> execute REST remediations -> rerun process_cost_basis ->
verify ready=True & manual confirmation persistence -> reopen & verify ready=False.
"""
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USDC
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.data_issues.constants import IssueKind
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.locations.constants import LOCATION_ETHEREUM, LOCATION_KRAKEN
from rotkehlchen.tasks.cost_basis import process_cost_basis
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_sync_response_with_result
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Price, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.assets.asset import Asset

pytestmark = pytest.mark.accounting_update

T0 = Timestamp(1_700_000_000)
T1 = Timestamp(1_700_010_000)
T2 = Timestamp(1_700_020_000)
T3 = Timestamp(1_700_030_000)
T4 = Timestamp(1_700_040_000)


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_pnl_data_issues_automated_agent_triage_loop(
        rotkehlchen_api_server: APIServer,
) -> None:
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
    rules_db.add_accounting_rule(
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
    for swap_subtype in (HistoryEventSubType.SPEND, HistoryEventSubType.RECEIVE):
        rules_db.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=swap_subtype,
            counterparty=None,
            rule=BaseEventSettings(
                taxable=True,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                accounting_treatment=TxAccountingTreatment.SWAP,
            ),
            links={},
        )

    events_db = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        # 1. Priced acquisition + unpriced spend -> MISSING_PRICE
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(T0 * 1000),
                location=LOCATION_ETHEREUM,
                location_label=TEST_ADDR1,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('1'),
            ),
        )
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(T1 * 1000),
                location=LOCATION_ETHEREUM,
                location_label=TEST_ADDR1,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('1'),
            ),
        )

        # 2. Spend of BTC with no prior lots -> MISSING_COST_BASIS
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(T2 * 1000),
                location=LOCATION_ETHEREUM,
                location_label=TEST_ADDR1,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_BTC,
                amount=FVal('0.5'),
            ),
        )

        # 3. Swap where USDC is ignored -> INCOMPLETE_SWAP
        database.add_to_ignored_assets(write_cursor=write_cursor, asset=A_USDC)
        swap_group = 'incomplete-swap-group-1'
        events_db.add_history_events(write_cursor=write_cursor, history=[
            SwapEvent(
                group_identifier=swap_group,
                sequence_index=0,
                timestamp=TimestampMS(T3 * 1000),
                location=LOCATION_ETHEREUM,
                location_label=TEST_ADDR1,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_USDC,
                amount=FVal('1000'),
            ),
            SwapEvent(
                group_identifier=swap_group,
                sequence_index=1,
                timestamp=TimestampMS(T3 * 1000),
                location=LOCATION_ETHEREUM,
                location_label=TEST_ADDR1,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_ETH,
                amount=FVal('0.5'),
            ),
        ])

        # 4. Unmatched exchange deposit -> UNMATCHED_EXCHANGE_TRANSFER
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=AssetMovement(
                group_identifier='kraken-deposit-1',
                timestamp=TimestampMS(T4 * 1000),
                location=LOCATION_KRAKEN,
                location_label='kraken',
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_ETH,
                amount=FVal('2'),
            ),
        )

    def query_historical_price(
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        # Allow manually stored historical prices to resolve via GlobalDB
        if (stored := GlobalDBHandler.get_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            max_seconds_distance=0,
            sources=(HistoricalPriceOracle.MANUAL,),
        )) is not None:
            return stored.price
        if from_asset == A_ETH and timestamp == T1:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )
        if from_asset == A_BTC:
            return Price(FVal('30000'))
        if from_asset == A_ETH and timestamp == T0:
            return Price(FVal('1000'))
        return Price(FVal('2000'))

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_historical_price
        assert process_cost_basis(database, database.msg_aggregator) is True

    # 1) Query realized PnL readiness: blocked by all 4 new IssueKinds
    pnl_before = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'realizedpnlresource'),
        json={},
    ))
    readiness = pnl_before['report_readiness']
    assert readiness['ready'] is False
    assert readiness['stale'] is False
    assert readiness['open_issues_by_kind'] == {
        IssueKind.INCOMPLETE_SWAP.value: 1,
        IssueKind.MISSING_COST_BASIS.value: 1,
        IssueKind.MISSING_PRICE.value: 1,
        IssueKind.UNMATCHED_EXCHANGE_TRANSFER.value: 1,
    }
    assert readiness['open_issues_count'] == 4

    # 2) Inspect open data issues & follow their machine-readable suggested_actions
    issues_resp = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
    ))
    issues_by_kind: dict[str, dict[str, Any]] = {
        entry['kind']: entry for entry in issues_resp['entries']
    }
    assert set(issues_by_kind) == {
        IssueKind.MISSING_PRICE.value,
        IssueKind.MISSING_COST_BASIS.value,
        IssueKind.INCOMPLETE_SWAP.value,
        IssueKind.UNMATCHED_EXCHANGE_TRANSFER.value,
    }

    # 2a) Remediate MISSING_PRICE via PUT /api/1/assets/prices/historical
    price_action = next(
        a for a in issues_by_kind[IssueKind.MISSING_PRICE.value]['suggested_actions']
        if a['action'] == 'set_manual_price'
    )
    assert price_action['endpoint'] == 'PUT /api/1/assets/prices/historical'
    assert_proper_sync_response_with_result(requests.put(
        api_url_for(rotkehlchen_api_server, 'historicalassetspriceresource'),
        json=price_action['params'] | {'price': '2500'},
    ))

    # 2b) Remediate MISSING_COST_BASIS via PATCH /resolve_manually (confirm_zero_basis)
    basis_issue = issues_by_kind[IssueKind.MISSING_COST_BASIS.value]
    confirm_action = next(
        a for a in basis_issue['suggested_actions']
        if a['action'] == 'confirm_zero_basis'
    )
    assert confirm_action['params'] == {'disposition': 'confirm_zero_basis'}
    assert_proper_sync_response_with_result(requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'dataissueresolvemanuallyresource',
            issue_id=basis_issue['id'],
        ),
        json=confirm_action['params'] | {'note': 'mined BTC'},
    ))

    # 2c) Remediate INCOMPLETE_SWAP via PATCH /resolve_manually (dismiss_as_standalone)
    swap_issue = issues_by_kind[IssueKind.INCOMPLETE_SWAP.value]
    standalone_action = next(
        a for a in swap_issue['suggested_actions']
        if a['action'] == 'dismiss_as_standalone'
    )
    assert standalone_action['params'] == {'disposition': 'dismiss_as_standalone'}
    assert_proper_sync_response_with_result(requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'dataissueresolvemanuallyresource',
            issue_id=swap_issue['id'],
        ),
        json=standalone_action['params'] | {'note': 'keep ETH leg'},
    ))

    # 2d) Remediate UNMATCHED_EXCHANGE_TRANSFER via PUT /history/events/match/asset_movements
    cex_issue = issues_by_kind[IssueKind.UNMATCHED_EXCHANGE_TRANSFER.value]
    external_action = next(
        a for a in cex_issue['suggested_actions']
        if a['action'] == 'resolve_as_external'
    )
    assert_proper_sync_response_with_result(requests.put(
        api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json=external_action['params'],
    ))

    # Verify manual_only filter returns the 2 confirmed issues
    confirmed_list = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
        params={'manual_only': 'true'},
    ))
    assert {entry['id'] for entry in confirmed_list['entries']} == {
        basis_issue['id'],
        swap_issue['id'],
    }

    # 3) Rerun process_cost_basis -> auto-resolved issues clear & manual confirmations persist
    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_historical_price
        assert process_cost_basis(database, database.msg_aggregator) is True

    pnl_after = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'realizedpnlresource'),
        json={},
    ))
    assert pnl_after['report_readiness']['ready'] is True
    assert pnl_after['report_readiness']['stale'] is False
    assert pnl_after['report_readiness']['open_issues_count'] == 0
    assert pnl_after['report_readiness']['open_issues_by_kind'] == {}
    assert pnl_after['num_unpriced_events'] == 0
    # ETH spend realized 2500 - 1000 = 1500; BTC 0.5 spend at 30000 with 0 basis = 15000;
    # dismissed-as-standalone ETH swap receive (0.5 * 2000 = 1000, taxable=True) -> 17500
    assert pnl_after['total_realized_pnl'] == '17500'

    # Confirmed issues stayed resolved across the rerun
    confirmed_after = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
        params={'manual_only': 'true'},
    ))
    assert {entry['id'] for entry in confirmed_after['entries']} == {
        basis_issue['id'],
        swap_issue['id'],
    }

    # 4) Reopen one confirmed issue -> readiness flips back to False
    reopened = assert_proper_sync_response_with_result(requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'dataissuereopenresource',
            issue_id=basis_issue['id'],
        ),
    ))
    assert reopened['state'] == 'open'
    pnl_reopened = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'realizedpnlresource'),
        json={},
    ))
    assert pnl_reopened['report_readiness']['ready'] is False
    assert pnl_reopened['report_readiness']['open_issues_by_kind'] == {
        IssueKind.MISSING_COST_BASIS.value: 1,
    }


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_unlink_and_link_ignore_asset_movement_marks_cost_basis_stale(
        rotkehlchen_api_server: APIServer,
) -> None:
    """Unlinking a matched movement, marking it no-match (link ignore), and clearing a no-match
    marker must all mark cost basis stale so process_cost_basis updates lots and issues."""
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    events_db = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=AssetMovement(
                group_identifier='kraken-seed',
                timestamp=TimestampMS((T0 - 100) * 1000),
                location=LOCATION_KRAKEN,
                location_label='kraken',
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_ETH,
                amount=FVal('1'),
            ),
        )
        withdrawal_id = events_db.add_history_event(
            write_cursor=write_cursor,
            event=AssetMovement(
                group_identifier='kraken-withdraw',
                timestamp=TimestampMS(T0 * 1000),
                location=LOCATION_KRAKEN,
                location_label='kraken',
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=FVal('1'),
            ),
        )
        onchain_receive_id = events_db.add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS((T0 + 10) * 1000),
                location=LOCATION_ETHEREUM,
                location_label=TEST_ADDR1,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('1'),
            ),
        )
    assert withdrawal_id is not None and onchain_receive_id is not None

    def query_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        return Price(FVal('2000'))

    # Match withdrawal to onchain receive and clear stale marker via process_cost_basis
    assert_proper_sync_response_with_result(requests.put(
        api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={
            'asset_movement': withdrawal_id,
            'matched_events': [onchain_receive_id],
            'external': False,
        },
    ))
    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_price
        assert process_cost_basis(database, database.msg_aggregator) is True

    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS) is None

    # 1) Unlink matched pair -> marks cost basis stale and re-emits UNMATCHED_EXCHANGE_TRANSFER
    assert_proper_sync_response_with_result(requests.delete(
        api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={'identifier': withdrawal_id},
    ))
    with database.conn.read_ctx() as cursor:
        stale_ts = database.get_static_cache(cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS)
    assert stale_ts is not None and int(stale_ts) <= T0 * 1000

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_price
        assert process_cost_basis(database, database.msg_aggregator) is True

    issues_after_unlink = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
        params={'kind': IssueKind.UNMATCHED_EXCHANGE_TRANSFER.value},
    ))
    assert withdrawal_id in {entry['event_identifier'] for entry in issues_after_unlink['entries']}

    # 2) Mark withdrawal as no-match (link ignore) -> marks stale & clears issue on rerun
    assert_proper_sync_response_with_result(requests.put(
        api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={'asset_movement': withdrawal_id, 'matched_events': [], 'external': False},
    ))
    with database.conn.read_ctx() as cursor:
        stale_ts = database.get_static_cache(cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS)
    assert stale_ts == str(T0 * 1000)

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_price
        assert process_cost_basis(database, database.msg_aggregator) is True

    issues_after_ignore = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
        params={'kind': IssueKind.UNMATCHED_EXCHANGE_TRANSFER.value},
    ))
    assert withdrawal_id not in {
        entry['event_identifier'] for entry in issues_after_ignore['entries']
    }

    # 3) Clearing link ignore via DELETE -> marks stale & re-emits issue on rerun
    assert_proper_sync_response_with_result(requests.delete(
        api_url_for(rotkehlchen_api_server, 'matchassetmovementsresource'),
        json={'identifier': withdrawal_id},
    ))
    with database.conn.read_ctx() as cursor:
        stale_ts = database.get_static_cache(cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS)
    assert stale_ts == str(T0 * 1000)

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price = query_price
        assert process_cost_basis(database, database.msg_aggregator) is True

    issues_after_unignore = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
        params={'kind': IssueKind.UNMATCHED_EXCHANGE_TRANSFER.value},
    ))
    assert withdrawal_id in {
        entry['event_identifier'] for entry in issues_after_unignore['entries']
    }
