"""Consumer-visible regressions for GET /balances/historical/reconciliation.

The setup helpers live in rotkehlchen.tests.utils.reconciliation so the same states can be
seeded in an isolated fixture server or the performance benchmark.
"""
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.history.data_issues.bucket_checks import BucketReason, BucketStatus
from rotkehlchen.history.data_issues.constants import IssueState
from rotkehlchen.locations.constants import (
    LOCATION_BANKS,
    LOCATION_BITCOIN,
    LOCATION_ETHEREUM,
    LOCATION_EXTERNAL,
    LOCATION_LOOPRING,
    LOCATION_OPTIMISM,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.reconciliation import (
    add_balance_bucket,
    add_check,
    add_complete_sync,
    add_empty_event,
    add_mismatch_issue,
    add_negative_balance_issue,
    add_observation,
    add_stop,
    clear_stale_marker,
    ignore_asset,
    latest_observation_id,
    seed_reconciliation_scenarios,
    set_stale_marker,
    track_blockchain_account,
)
from rotkehlchen.types import SupportedBlockchain
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms

pytestmark = [
    pytest.mark.accounting_update,
    pytest.mark.parametrize('use_clean_caching_directory', [True]),
    pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]]),
]

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.locations.types import LocationIdentifier


def _report(server: APIServer, **params: object) -> dict:
    return assert_proper_sync_response_with_result(requests.get(
        api_url_for(server, 'historicalbalancesreconciliationresource'),
        json=params or None,
    ))


def _account(result: dict, location: str, label: str) -> dict:
    return next(
        account for account in result['accounts']
        if account['location'] == location and account['location_label'] == label
    )


def _bucket(account: dict, asset: str, protocol: str | None = None) -> dict:
    return next(
        bucket for bucket in account['buckets']
        if bucket['asset'] == asset and bucket['protocol'] == protocol
    )


def test_summary_counts_and_scoped_detail(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    seeded = seed_reconciliation_scenarios(database, (TEST_ADDR1, TEST_ADDR2))

    result = _report(rotkehlchen_api_server)
    assert result['stale'] is False
    assert result['processing'] is False
    assert result['buckets_total'] == 6
    assert result['totals'] == {
        'reconciled': 1,
        'mismatch': 1,
        'blocked': 1,
        'pending': 1,
        'not_compared': 2,
    }
    assert {account['location'] for account in result['accounts']} == {
        LOCATION_ETHEREUM, LOCATION_OPTIMISM, 'kraken',
    }
    assert 'buckets' not in result['accounts'][0]  # lazy: only a scoped request expands
    main_account = _account(result, LOCATION_ETHEREUM, TEST_ADDR1)
    assert main_account['counts'] == {
        'reconciled': 1,
        'mismatch': 0,
        'blocked': 0,
        'pending': 0,
        'not_compared': 1,
    }
    assert main_account['last_compared_at'] is not None
    assert main_account['last_event_ts'] is not None
    assert main_account['history_synced_to'] is not None
    assert _account(result, LOCATION_ETHEREUM, TEST_ADDR2)['counts'][BucketStatus.MISMATCH] == 1
    pending_account = seeded['never_compared']['account']
    pending_counts = _account(result, LOCATION_ETHEREUM, pending_account)['counts']
    assert pending_counts[BucketStatus.PENDING] == 1
    exchange = _account(result, 'kraken', 'kraken account')
    assert exchange['is_exchange'] is True
    assert exchange['counts'][BucketStatus.NOT_COMPARED] == 1
    assert _account(result, LOCATION_OPTIMISM, TEST_ADDR1)['counts'][BucketStatus.BLOCKED] == 1

    scoped = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
    )
    assert len(scoped['accounts']) == 1
    # location/location_label scope the totals; the status filter is what never changes them.
    assert scoped['totals'] == {
        'reconciled': 1,
        'mismatch': 0,
        'blocked': 0,
        'pending': 0,
        'not_compared': 1,
    }
    account = scoped['accounts'][0]
    assert account['pagination'] == {'limit': 50, 'offset': 0, 'total': 2}
    assert len(account['buckets']) == 2
    reconciled = _bucket(account, A_ETH.identifier)
    assert reconciled['status'] == BucketStatus.RECONCILED
    assert reconciled['reasons'] == []
    assert reconciled['derived_balance'] == '5'
    assert reconciled['observed_balance'] == '5'
    assert reconciled['check']['derived_balance'] == '5'
    assert reconciled['check']['observed_balance'] == '5'
    assert reconciled['check']['delta'] == '0'
    assert reconciled['observed_at'] is not None
    assert reconciled['check']['compared_at'] is not None
    assert reconciled['last_event_ts'] is not None
    assert reconciled['stop'] is None

    mismatch_scoped = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR2,
    )['accounts'][0]
    mismatch = next(
        bucket for bucket in mismatch_scoped['buckets']
        if bucket['status'] == BucketStatus.MISMATCH
    )
    assert mismatch['asset'] in {seeded['mismatch']['asset'], A_ETH.identifier}
    assert mismatch['check']['delta'] == seeded['mismatch']['delta']
    protocol = _bucket(account, A_ETH.identifier, 'aave-v3')
    assert protocol['status'] == BucketStatus.NOT_COMPARED
    assert protocol['reasons'] == ['protocol_bucket', 'never_compared']
    assert protocol['observed_balance'] is None


def test_status_filter_and_pagination_keep_totals(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    seed_reconciliation_scenarios(database, (TEST_ADDR1, TEST_ADDR2))

    unfiltered = _report(rotkehlchen_api_server)
    scoped_unfiltered = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
    )
    filtered = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
        status='reconciled',
    )
    # The status filter filters rows only; the scoped totals do not change with it.
    assert filtered['totals'] == scoped_unfiltered['totals']
    assert scoped_unfiltered['totals'] != unfiltered['totals']
    account = filtered['accounts'][0]
    assert account['counts'][BucketStatus.RECONCILED] == 1  # counts stay unfiltered
    assert account['counts'][BucketStatus.MISMATCH] == 0
    assert account['counts'][BucketStatus.NOT_COMPARED] == 1
    assert [bucket['status'] for bucket in account['buckets']] == ['reconciled']
    assert account['pagination']['total'] == 1

    paged = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
        limit=1,
        offset=1,
    )
    account = paged['accounts'][0]
    assert len(account['buckets']) == 1
    assert account['pagination'] == {'limit': 1, 'offset': 1, 'total': 2}
    assert paged['totals'] == scoped_unfiltered['totals']

    invalid = requests.get(
        api_url_for(rotkehlchen_api_server, 'historicalbalancesreconciliationresource'),
        json={'status': 'not_a_status'},
    )
    assert invalid.status_code == HTTPStatus.BAD_REQUEST


def test_blocked_bucket_with_no_metric_keeps_dismissed_issue(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    seeded = seed_reconciliation_scenarios(database, (TEST_ADDR1, TEST_ADDR2))

    result = _report(
        rotkehlchen_api_server,
        location=LOCATION_OPTIMISM,
        location_label=TEST_ADDR1,
    )
    account = result['accounts'][0]
    assert account['counts'][BucketStatus.BLOCKED] == 1
    bucket = account['buckets'][0]
    assert bucket['status'] == BucketStatus.BLOCKED
    assert bucket['derived_balance'] is None  # failed processing, never a synthetic zero
    assert bucket['observed_balance'] is None
    assert bucket['check'] is None
    assert bucket['stop']['event_identifier'] == seeded['blocked']['event_identifier']
    assert bucket['stop']['event_timestamp'] == ts_sec_to_ms(seeded['blocked']['event_ts'])
    assert bucket['stop']['derived_balance_before_event'] == '1'
    assert bucket['stop']['negative_amount'] == '-2'
    with database.conn.read_ctx() as cursor:
        group_identifier = cursor.execute(
            'SELECT group_identifier FROM history_events WHERE identifier = ?',
            (seeded['blocked']['event_identifier'],),
        ).fetchone()[0]
    assert bucket['stop']['group_identifier'] == group_identifier
    assert bucket['issue_id'] == seeded['blocked']['issue_id']
    assert result['totals'][BucketStatus.BLOCKED] == 1

    # The issue is dismissed, which does not clear or hide the stop.
    with database.conn.read_ctx() as cursor:
        state = cursor.execute(
            'SELECT state FROM data_issues WHERE id = ?',
            (seeded['blocked']['issue_id'],),
        ).fetchone()[0]
    assert state == IssueState.DISMISSED.value


def test_unknown_sides_stay_null_and_never_compared_is_pending(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    add_balance_bucket(database, TEST_ADDR1, '4', ts_now() - 3_600)
    add_empty_event(database, TEST_ADDR1, ts_now() - 1_800)  # event with no metric yet
    add_complete_sync(database, TEST_ADDR1, ts_now() - 10)

    scoped = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
    )
    assert scoped['processing'] is True  # an event without a metric means processing is due
    bucket = scoped['accounts'][0]['buckets'][0]
    assert bucket['status'] == BucketStatus.PENDING
    assert BucketReason.NEVER_COMPARED in bucket['reasons']
    assert bucket['observed_balance'] is None  # no observation, not zero
    assert bucket['check'] is None
    assert bucket['derived_balance'] == '4'
    assert scoped['totals'][BucketStatus.PENDING] == 1


def test_ignored_assets_and_untracked_accounts_are_out_of_scope(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    seed_reconciliation_scenarios(database, (TEST_ADDR1, TEST_ADDR2))
    ignore_asset(database, A_ETH2)
    untracked = make_evm_address()
    add_balance_bucket(database, untracked, '9', ts_now() - 3_600)

    result = _report(rotkehlchen_api_server)
    assert result['buckets_total'] == 5
    assert untracked not in {account['location_label'] for account in result['accounts']}
    scoped = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
    )
    assert A_ETH2.identifier not in {
        bucket['asset'] for bucket in scoped['accounts'][0]['buckets']
    }


def test_stale_history_turns_a_saved_match_pending_but_not_a_blocked_bucket(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    seed_reconciliation_scenarios(database, (TEST_ADDR1, TEST_ADDR2))
    set_stale_marker(database, ts_now() - 100)

    scoped = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
    )
    assert scoped['stale'] is True
    account = scoped['accounts'][0]
    reconciled = _bucket(account, A_ETH.identifier)
    assert reconciled['status'] == BucketStatus.PENDING
    assert BucketReason.DERIVED_HISTORY_STALE in reconciled['reasons']
    assert account['counts'][BucketStatus.PENDING] == 1
    assert account['counts'][BucketStatus.RECONCILED] == 0

    blocked = _report(
        rotkehlchen_api_server,
        location=LOCATION_OPTIMISM,
        location_label=TEST_ADDR1,
    )['accounts'][0]['buckets'][0]
    assert blocked['status'] == BucketStatus.BLOCKED
    assert BucketReason.DERIVED_HISTORY_STALE in blocked['reasons']

    clear_stale_marker(database)
    restored = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
    )
    assert _bucket(restored['accounts'][0], A_ETH.identifier)['status'] == BucketStatus.RECONCILED


def test_replaced_observation_supersedes_a_saved_check(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    now = ts_now()
    event_id = add_balance_bucket(database, TEST_ADDR1, '5', now - 3_600)
    add_complete_sync(database, TEST_ADDR1, now)
    add_observation(database, TEST_ADDR1, A_ETH, '5', now - 120)
    with database.conn.read_ctx() as cursor:
        first_observation_id = cursor.execute(
            'SELECT observation_id FROM wallet_balance_observations WHERE address = ?',
            (TEST_ADDR1,),
        ).fetchone()[0]
    add_check(
        database=database,
        address=TEST_ADDR1,
        derived_balance='5',
        observed_balance='5',
        observed_at=now - 120,
        latest_event_identifier=event_id,
        observation_id=first_observation_id,
    )
    assert _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
    )['accounts'][0]['buckets'][0]['status'] == BucketStatus.RECONCILED

    # A second successful query within the same second replaces the observation identity.
    add_observation(database, TEST_ADDR1, A_ETH, '5', now - 120)
    bucket = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
    )['accounts'][0]['buckets'][0]
    assert bucket['status'] == BucketStatus.PENDING
    assert BucketReason.OBSERVATION_SUPERSEDED in bucket['reasons']


def test_issue_links_use_the_exact_bucket_and_stopping_event(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    _treat_eth2_as_eth(database, enabled=False)  # keep the ETH2 issue bucket separate
    now = ts_now()
    for address in (TEST_ADDR1, TEST_ADDR2):
        event_id = add_balance_bucket(database, address, '5', now - 3_600)
        add_observation(database, address, A_ETH, '7', now - 120)
        add_complete_sync(database, address, now)
        add_check(
            database=database,
            address=address,
            derived_balance='5',
            observed_balance='7',
            observed_at=now - 120,
            latest_event_identifier=event_id,
            observation_id=latest_observation_id(database, address, A_ETH),
        )
    first_issue = add_mismatch_issue(database, TEST_ADDR1)
    second_issue = add_mismatch_issue(database, TEST_ADDR2)
    add_mismatch_issue(database, TEST_ADDR1, asset=A_ETH2)  # another bucket, same account

    result = _report(rotkehlchen_api_server)
    assert _account(result, LOCATION_ETHEREUM, TEST_ADDR1)['counts'][BucketStatus.MISMATCH] == 1
    first = _report(
        rotkehlchen_api_server, location=LOCATION_ETHEREUM, location_label=TEST_ADDR1,
    )['accounts'][0]['buckets'][0]
    second = _report(
        rotkehlchen_api_server, location=LOCATION_ETHEREUM, location_label=TEST_ADDR2,
    )['accounts'][0]['buckets'][0]
    assert first['issue_id'] == first_issue
    assert second['issue_id'] == second_issue

    # A negative-balance issue that is not the stopping event must not be linked to the stop.
    track_blockchain_account(database, TEST_ADDR1, SupportedBlockchain.OPTIMISM)
    add_balance_bucket(database, TEST_ADDR1, '1', now - 3_600, location=LOCATION_OPTIMISM)
    stop_event = add_empty_event(database, TEST_ADDR1, now - 3_000, location=LOCATION_OPTIMISM)
    other_event = add_empty_event(database, TEST_ADDR1, now - 2_000, location=LOCATION_OPTIMISM)
    add_stop(
        database=database,
        address=TEST_ADDR1,
        event_identifier=stop_event,
        event_timestamp=now - 3_000,
        location=LOCATION_OPTIMISM,
    )
    add_negative_balance_issue(
        database=database,
        address=TEST_ADDR1,
        event_identifier=other_event,
        location=LOCATION_OPTIMISM,
    )
    blocked = _report(
        rotkehlchen_api_server, location=LOCATION_OPTIMISM, location_label=TEST_ADDR1,
    )['accounts'][0]['buckets'][0]
    assert blocked['status'] == BucketStatus.BLOCKED
    assert blocked['issue_id'] is None


def test_non_evm_bucket_is_not_compared(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    bitcoin_address = 'bc1qtestaddress'
    track_blockchain_account(database, bitcoin_address, SupportedBlockchain.BITCOIN)
    add_balance_bucket(
        database=database,
        address=bitcoin_address,
        amount='1',
        ts=ts_now() - 3_600,
        location=LOCATION_BITCOIN,
    )

    result = _report(
        rotkehlchen_api_server,
        location=LOCATION_BITCOIN,
        location_label=bitcoin_address,
    )
    bucket = result['accounts'][0]['buckets'][0]
    assert bucket['status'] == BucketStatus.NOT_COMPARED
    assert BucketReason.NON_EVM_CHAIN in bucket['reasons']
    assert bucket['derived_balance'] == '1'  # a metric exists; only comparison is unsupported


@pytest.mark.parametrize('location', [LOCATION_EXTERNAL, LOCATION_BANKS, LOCATION_LOOPRING])
@pytest.mark.parametrize('stale', [False, True])
def test_unsupported_location_is_not_compared(
        rotkehlchen_api_server: APIServer,
        location: LocationIdentifier,
        stale: bool,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    add_balance_bucket(
        database=database,
        address=(label := 'imported account'),
        amount='1',
        ts=(timestamp := ts_now() - 3_600),
        location=location,
    )
    if stale:
        set_stale_marker(database, timestamp)

    summary = _report(rotkehlchen_api_server)
    assert summary['totals'][BucketStatus.NOT_COMPARED] == 1
    assert summary['totals'][BucketStatus.PENDING] == 0
    assert _account(summary, location, label)['counts'][BucketStatus.NOT_COMPARED] == 1
    bucket = _report(
        rotkehlchen_api_server, location=location, location_label=label,
    )['accounts'][0]['buckets'][0]
    assert bucket['status'] == BucketStatus.NOT_COMPARED
    assert 'unsupported_location' in bucket['reasons']
    assert bucket['derived_balance'] == '1'


def test_tracked_account_without_buckets_is_still_listed(
        rotkehlchen_api_server: APIServer,
) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    fresh_address = make_evm_address()
    track_blockchain_account(database, fresh_address)  # tracked but never synced or queried

    result = _report(rotkehlchen_api_server)
    account = _account(result, LOCATION_ETHEREUM, fresh_address)
    assert account['counts'] == {
        'reconciled': 0,
        'mismatch': 0,
        'blocked': 0,
        'pending': 0,
        'not_compared': 0,
    }
    assert account['last_compared_at'] is None
    assert account['last_event_ts'] is None
    assert account['history_synced_to'] is None
    assert result['buckets_total'] == 0
    # Both fixture accounts are tracked too, so an empty list really would mean "no accounts".
    assert len(result['accounts']) == 3

    scoped = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label=fresh_address,
    )
    assert scoped['accounts'][0]['buckets'] == []
    assert scoped['accounts'][0]['pagination'] == {'limit': 50, 'offset': 0, 'total': 0}


def test_null_label_account_is_expandable(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    add_balance_bucket(
        database=database,
        address=None,
        amount='3',
        ts=ts_now() - 3_600,
        protocol='aave-v3',
    )

    summary = _report(rotkehlchen_api_server)
    account = next(
        account for account in summary['accounts']
        if account['location'] == LOCATION_ETHEREUM and account['location_label'] is None
    )
    assert account['counts']['not_compared'] == 1
    assert 'buckets' not in account

    # An empty location_label is the explicit scope of the null-label account.
    scoped = _report(
        rotkehlchen_api_server,
        location=LOCATION_ETHEREUM,
        location_label='',
    )
    assert len(scoped['accounts']) == 1
    assert scoped['accounts'][0]['location_label'] is None
    assert scoped['accounts'][0]['pagination'] == {'limit': 50, 'offset': 0, 'total': 1}
    assert scoped['accounts'][0]['buckets'][0]['protocol'] == 'aave-v3'

    # Without a location the empty label is not an account scope, so no buckets are returned.
    unscoped = _report(rotkehlchen_api_server, location_label='')
    assert all('buckets' not in account for account in unscoped['accounts'])


def _treat_eth2_as_eth(database, enabled: bool = True) -> None:
    with database.user_write() as write_cursor:
        database.set_settings(
            write_cursor=write_cursor,
            settings=ModifiableDBSettings(treat_eth2_as_eth=enabled),
        )


def test_eth2_stop_blocks_a_folded_eth_match(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    _treat_eth2_as_eth(database)
    now = ts_now()
    event_id = add_balance_bucket(database, TEST_ADDR1, '5', now - 3_600)
    add_observation(database, TEST_ADDR1, A_ETH, '5', now - 120)
    add_complete_sync(database, TEST_ADDR1, now)
    add_check(
        database=database,
        address=TEST_ADDR1,
        derived_balance='5',
        observed_balance='5',
        observed_at=now - 120,
        latest_event_identifier=event_id,
        observation_id=latest_observation_id(database, TEST_ADDR1, A_ETH),
    )
    baseline = _report(
        rotkehlchen_api_server, location=LOCATION_ETHEREUM, location_label=TEST_ADDR1,
    )['accounts'][0]
    assert _bucket(baseline, A_ETH.identifier)['status'] == BucketStatus.RECONCILED

    # A pass that ran with the setting off recorded the stop under ETH2.
    stop_event = add_empty_event(database, TEST_ADDR1, now - 3_000)
    add_stop(
        database=database,
        address=TEST_ADDR1,
        event_identifier=stop_event,
        event_timestamp=now - 3_000,
        asset=A_ETH2,
    )
    scoped = _report(
        rotkehlchen_api_server, location=LOCATION_ETHEREUM, location_label=TEST_ADDR1,
    )
    account = scoped['accounts'][0]
    assert len(account['buckets']) == 1  # one folded bucket, not an ETH2 stop beside it
    bucket = account['buckets'][0]
    assert bucket['asset'] == A_ETH.identifier
    assert bucket['status'] == BucketStatus.BLOCKED
    assert bucket['derived_balance'] == '5'
    assert bucket['issue_id'] is None  # the stop predates any issue for it
    assert account['counts'][BucketStatus.BLOCKED] == 1
    assert scoped['totals'][BucketStatus.BLOCKED] == 1
    assert scoped['totals'][BucketStatus.RECONCILED] == 0


def test_negative_issues_link_only_their_own_bucket(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    now = ts_now()
    stop_event = add_empty_event(database, TEST_ADDR1, now - 3_000)
    add_stop(
        database=database,
        address=TEST_ADDR1,
        event_identifier=stop_event,
        event_timestamp=now - 3_000,
    )
    add_stop(
        database=database,
        address=TEST_ADDR1,
        event_identifier=stop_event,
        event_timestamp=now - 3_000,
        protocol='aave-v3',
    )
    wallet_issue = add_negative_balance_issue(database, TEST_ADDR1, stop_event)
    protocol_issue = add_negative_balance_issue(
        database=database,
        address=TEST_ADDR1,
        event_identifier=stop_event,
        protocol='aave-v3',
    )
    # A stop without any issue keeps its blocked row and stays unlinked.
    orphan_event = add_empty_event(database, TEST_ADDR2, now - 3_000)
    add_stop(
        database=database,
        address=TEST_ADDR2,
        event_identifier=orphan_event,
        event_timestamp=now - 3_000,
    )

    account = _report(
        rotkehlchen_api_server, location=LOCATION_ETHEREUM, location_label=TEST_ADDR1,
    )['accounts'][0]
    assert _bucket(account, A_ETH.identifier)['status'] == BucketStatus.BLOCKED
    assert _bucket(account, A_ETH.identifier)['issue_id'] == wallet_issue
    assert _bucket(account, A_ETH.identifier, 'aave-v3')['status'] == BucketStatus.BLOCKED
    assert _bucket(account, A_ETH.identifier, 'aave-v3')['issue_id'] == protocol_issue
    orphan = _report(
        rotkehlchen_api_server, location=LOCATION_ETHEREUM, location_label=TEST_ADDR2,
    )['accounts'][0]['buckets'][0]
    assert orphan['status'] == BucketStatus.BLOCKED
    assert orphan['issue_id'] is None


def test_mismatch_issue_is_linked_after_asset_folding(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    _treat_eth2_as_eth(database)
    now = ts_now()
    event_id = add_balance_bucket(database, TEST_ADDR1, '5', now - 3_600)
    add_observation(database, TEST_ADDR1, A_ETH, '7', now - 120)
    add_complete_sync(database, TEST_ADDR1, now)
    add_check(
        database=database,
        address=TEST_ADDR1,
        derived_balance='5',
        observed_balance='7',
        observed_at=now - 120,
        latest_event_identifier=event_id,
        observation_id=latest_observation_id(database, TEST_ADDR1, A_ETH),
    )
    issue_id = add_mismatch_issue(database, TEST_ADDR1, asset=A_ETH2)

    bucket = _report(
        rotkehlchen_api_server, location=LOCATION_ETHEREUM, location_label=TEST_ADDR1,
    )['accounts'][0]['buckets'][0]
    assert bucket['asset'] == A_ETH.identifier
    assert bucket['status'] == BucketStatus.MISMATCH
    assert bucket['issue_id'] == issue_id


def test_feature_gate(rotkehlchen_api_server: APIServer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ROTKI_ACCOUNTING_UPDATE', 'False')
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'historicalbalancesreconciliationresource',
    ))
    assert_error_response(
        response,
        contained_in_msg='Historical balance reconciliation is disabled',
        status_code=HTTPStatus.NOT_FOUND,
    )
