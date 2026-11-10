"""Focused coverage for asset-specific wallet observations and comparison eligibility."""
from typing import Final
from unittest.mock import patch

import pytest

from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.evmtx import evm_tx_query_range_prefixes
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.bucket_checks import (
    BucketBalanceCheck,
    BucketReason,
    BucketStatus,
    DerivedSnapshot,
    classify_bucket,
    get_balance_checks,
    save_balance_check,
)
from rotkehlchen.history.data_issues.detectors.current_balance import (
    CurrentBalanceMismatchDetector,
)
from rotkehlchen.history.data_issues.eligibility import (
    get_wallet_evidence,
    get_wallet_evidence_bulk,
)
from rotkehlchen.history.data_issues.observations import (
    ObservationSource,
    get_wallet_observations,
    record_token_detection_observations,
    record_wallet_observations,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import EventMetricKey, SupportedBlockchain, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now

pytestmark = [
    pytest.mark.accounting_update,
    pytest.mark.parametrize('use_clean_caching_directory', [True]),
    pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]]),
]

TOKEN: Final = 'eip155:1/erc20:0x0012940cf77a3cB5BADE409B96A60E22506CF7d0'


def _observe(
        database,
        address: str,
        asset: str,
        amount: str,
        observed_at: int,
) -> None:
    with database.user_write() as write_cursor:
        record_wallet_observations(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            address=address,
            amounts={asset: FVal(amount)},
            observed_at=Timestamp(observed_at),
            source=ObservationSource.BALANCE_QUERY,
        )


def _sync(database, address: str, end: int, start: int = 0) -> None:
    with database.user_write() as write_cursor:
        for prefix in evm_tx_query_range_prefixes(SupportedBlockchain.ETHEREUM):
            database.update_used_query_range(
                write_cursor=write_cursor,
                name=f'{prefix}_{address}',
                start_ts=Timestamp(start),
                end_ts=Timestamp(end),
            )


def _derive(database, address: str, amount: str, asset=A_ETH, ts: int = 1_000) -> None:
    with database.user_write() as write_cursor:
        event_id = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(ts),
                location=LOCATION_ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                amount=FVal(amount),
                location_label=address,
            ),
        )
        write_cursor.execute(
            'INSERT INTO event_metrics(event_identifier, location, location_label, protocol, '
            'metric_key, metric_value, asset, timestamp, sequence_index, sort_key) '
            'VALUES (?, ?, ?, NULL, ?, ?, ?, ?, 0, ?)',
            (
                event_id, LOCATION_ETHEREUM, address,
                EventMetricKey.BALANCE.serialize(), amount, asset.identifier, ts, ts,
            ),
        )


def test_zero_observation_differs_from_unknown(database) -> None:
    address = TEST_ADDR1
    now = ts_now()
    _sync(database, address, end=now)

    # Never queried: no observation, so the amount is unknown, not zero.
    evidence = get_wallet_evidence(
        database=database,
        location=LOCATION_ETHEREUM,
        address=address,
        asset=A_ETH.identifier,
        derived=None,
    )
    assert evidence.amount is None
    assert BucketReason.OBSERVATION_MISSING in evidence.pending_reasons
    assert evidence.verified_history_free is True  # cheap check: no events and synced

    # A successful query that found nothing writes an explicit zero.
    _observe(database, address, A_ETH.identifier, '0', now)
    evidence = get_wallet_evidence(
        database=database,
        location=LOCATION_ETHEREUM,
        address=address,
        asset=A_ETH.identifier,
        derived=None,
    )
    assert evidence.amount == FVal(0)
    assert evidence.pending_reasons == ()
    assert evidence.derived_snapshot is not None
    assert evidence.derived_snapshot.is_history_free is True


def test_token_detection_only_replaces_its_own_provenance(database) -> None:
    address = TEST_ADDR1
    now = ts_now()
    _observe(database, address, A_ETH.identifier, '1', now)
    _observe(database, address, TOKEN, '5', now)
    unrelated = make_evm_address()
    _observe(database, unrelated, A_ETH.identifier, '2', now)
    before = get_wallet_observations(database)

    with database.user_write() as write_cursor:
        record_token_detection_observations(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            address=address,
            amounts={},  # detection found the token gone
            previous_assets=(TOKEN,),
            queried_assets=(TOKEN,),
            observed_at=Timestamp(now + 1),
        )

    after = get_wallet_observations(database)
    assert after[LOCATION_ETHEREUM, address, TOKEN].amount == FVal(0)
    assert after[LOCATION_ETHEREUM, address, TOKEN].observation_id != before[LOCATION_ETHEREUM, address, TOKEN].observation_id  # noqa: E501
    # The native balance was not queried by token detection and keeps its provenance.
    assert after[LOCATION_ETHEREUM, address, A_ETH.identifier] == before[LOCATION_ETHEREUM, address, A_ETH.identifier]  # noqa: E501
    assert after[LOCATION_ETHEREUM, unrelated, A_ETH.identifier] == before[LOCATION_ETHEREUM, unrelated, A_ETH.identifier]  # noqa: E501


@pytest.mark.parametrize('legacy_check', [False, True])
def test_same_second_replacement_supersedes_a_saved_match(database, legacy_check: bool) -> None:
    address = TEST_ADDR1
    now = ts_now()
    _sync(database, address, end=now)
    _observe(database, address, A_ETH.identifier, '1', now)
    observation = get_wallet_observations(database)[LOCATION_ETHEREUM, address, A_ETH.identifier]
    with database.user_write() as write_cursor:
        save_balance_check(write_cursor, BucketBalanceCheck(
            location=LOCATION_ETHEREUM,
            location_label=address,
            asset=A_ETH.identifier,
            derived_balance=FVal(1),
            observed_balance=FVal(1),
            latest_event_identifier=None,
            observed_at=observation.observed_at,
            compared_at=Timestamp(now),
            observation_id=None if legacy_check else observation.observation_id,
        ))

    # Same second, same amount, but a different query result identity.
    _observe(database, address, A_ETH.identifier, '1', now)
    latest = get_wallet_observations(database)[LOCATION_ETHEREUM, address, A_ETH.identifier]
    assert latest.observation_id != observation.observation_id
    with database.conn.read_ctx() as cursor:
        check = get_balance_checks(cursor)[LOCATION_ETHEREUM, address, A_ETH.identifier]

    classification = classify_bucket(
        is_blocked=False,
        unsupported=(),
        check=check,
        derived=DerivedSnapshot(balance=FVal(1), latest_event_identifier=None),
        is_derived_history_stale=False,
        latest_observed_at=latest.observed_at,
        latest_observation_id=latest.observation_id,
        now=Timestamp(now),
        tolerance=FVal('0.001'),
    )
    assert classification.status == BucketStatus.PENDING
    assert BucketReason.OBSERVATION_SUPERSEDED in classification.reasons


def test_sync_start_boundary_and_missing_receipt_pending(database) -> None:
    address = TEST_ADDR1
    now = ts_now()
    _observe(database, address, A_ETH.identifier, '0', now)

    # A range that starts after genesis leaves earlier transactions unqueried.
    _sync(database, address, end=now, start=100)
    evidence = get_wallet_evidence(
        database=database,
        location=LOCATION_ETHEREUM,
        address=address,
        asset=A_ETH.identifier,
        derived=None,
    )
    assert BucketReason.HISTORY_NOT_SYNCED in evidence.pending_reasons
    assert evidence.verified_history_free is False

    # A transaction mapped to the address without a receipt still has no decoded marker.
    _sync(database, address, end=now)
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO evm_transactions(identifier, tx_hash, chain_id, timestamp, block_number, '
            'from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce) '
            'VALUES (1, ?, ?, ?, 1, ?, ?, "0", "21000", "1", "21000", "", 0)',
            (make_evm_tx_hash(), SupportedBlockchain.ETHEREUM.to_chain_id().serialize_for_db(), now, address, address),  # noqa: E501
        )
        write_cursor.execute(
            'INSERT INTO evmtx_address_mappings(tx_id, address) VALUES (1, ?)',
            (address,),
        )
    evidence = get_wallet_evidence(
        database=database,
        location=LOCATION_ETHEREUM,
        address=address,
        asset=A_ETH.identifier,
        derived=None,
    )
    assert BucketReason.HISTORY_PENDING_DECODING in evidence.pending_reasons
    assert evidence.verified_history_free is False


def test_observed_only_holding_is_detected(database) -> None:
    address = TEST_ADDR1
    now = ts_now()
    _sync(database, address, end=now)
    _observe(database, address, TOKEN, '3', now)

    assert CurrentBalanceMismatchDetector(database=database).run() == 1
    with database.conn.read_ctx() as cursor:
        check = get_balance_checks(cursor)[LOCATION_ETHEREUM, address, TOKEN]
    assert check.derived_balance == FVal(0)
    assert check.observed_balance == FVal(3)


def test_history_free_zero_is_reconciled(database) -> None:
    address = TEST_ADDR1
    now = ts_now()
    _sync(database, address, end=now)
    _observe(database, address, A_ETH.identifier, '0', now)

    assert CurrentBalanceMismatchDetector(database=database).run() == 1
    with database.conn.read_ctx() as cursor:
        check = get_balance_checks(cursor)[LOCATION_ETHEREUM, address, A_ETH.identifier]
    assert check.derived_balance == FVal(0)
    assert check.observed_balance == FVal(0)


def test_derived_asset_without_coverage_is_not_compared(database) -> None:
    address = TEST_ADDR1
    now = ts_now()
    _derive(database, address, '5')
    _sync(database, address, end=now)

    assert CurrentBalanceMismatchDetector(database=database).run() == 0
    with database.conn.read_ctx() as cursor:
        assert get_balance_checks(cursor) == {}
    evidence = get_wallet_evidence(
        database=database,
        location=LOCATION_ETHEREUM,
        address=address,
        asset=A_ETH.identifier,
        derived=DerivedSnapshot(balance=FVal(5), latest_event_identifier=1, latest_ts=TimestampMS(1_000)),  # noqa: E501
    )
    assert BucketReason.OBSERVATION_MISSING in evidence.pending_reasons


def test_rebasing_bucket_is_not_compared(database, monkeypatch) -> None:
    address = TEST_ADDR1
    now = ts_now()
    _observe(database, address, TOKEN, '3', now)
    _sync(database, address, end=now)
    monkeypatch.setattr(
        'rotkehlchen.history.data_issues.eligibility.GlobalDBHandler.get_asset_ids_with_flag',
        staticmethod(lambda flag: frozenset({TOKEN})),
    )

    assert CurrentBalanceMismatchDetector(database=database).run() == 0
    with database.conn.read_ctx() as cursor:
        assert get_balance_checks(cursor) == {}


def test_bulk_evidence_matches_single_lookup(database) -> None:
    address = TEST_ADDR1
    now = ts_now()
    _observe(database, address, A_ETH.identifier, '0', now)
    _sync(database, address, end=now)
    key = (LOCATION_ETHEREUM, address, A_ETH.identifier)
    single = get_wallet_evidence(
        database=database, location=key[0], address=key[1], asset=key[2], derived=None,
    )
    bulk = get_wallet_evidence_bulk(database=database, derived={key: None})
    assert bulk[key] == single


@pytest.mark.parametrize(
    'remove_account', [False, True], ids=['history-reset', 'remove-and-readd'],
)
def test_cleared_history_drops_observations(database, remove_account: bool) -> None:
    if not remove_account:
        _derive(database, TEST_ADDR1, '1')
        process_historical_balances(database=database, msg_aggregator=database.msg_aggregator)
    _sync(database, TEST_ADDR1, end=(now := ts_now()))
    _observe(database, TEST_ADDR1, A_ETH.identifier, '1', now)
    detector = CurrentBalanceMismatchDetector(database=database)
    assert detector.run() == 1

    with database.user_write() as write_cursor:
        if remove_account:
            database.remove_single_blockchain_accounts(
                write_cursor=write_cursor,
                blockchain=SupportedBlockchain.ETHEREUM,
                accounts=[TEST_ADDR1],
            )
            write_cursor.execute(
                'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
                (SupportedBlockchain.ETHEREUM.value, TEST_ADDR1),
            )
        else:
            DBHistoryEvents(database).delete_events_and_track(
                write_cursor, 'WHERE location=? AND location_label=?',
                (LOCATION_ETHEREUM, TEST_ADDR1),
            )

    assert detector.run() == 0
    process_historical_balances(database=database, msg_aggregator=database.msg_aggregator)
    _sync(database, TEST_ADDR1, end=now)
    assert detector.run() == 0
    assert get_wallet_observations(database) == {}
    with database.conn.read_ctx() as cursor:
        assert get_balance_checks(cursor) == {}

    _observe(database, TEST_ADDR1, A_ETH.identifier, '1', now)
    assert detector.run() == 1


def test_last_address_stamp_alone_is_not_zero_coverage(database) -> None:
    address = TEST_ADDR1
    with database.user_write() as write_cursor:
        database.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.LAST_ADDRESS_BALANCES_QUERY_TS,
            value=Timestamp(ts_now()),
            blockchain=SupportedBlockchain.ETHEREUM.serialize(),
            address=address,
        )
    evidence = get_wallet_evidence(
        database=database,
        location=LOCATION_ETHEREUM,
        address=address,
        asset=A_ETH.identifier,
        derived=None,
    )
    assert evidence.amount is None
    assert BucketReason.ASSET_COVERAGE_MISSING in evidence.pending_reasons


@pytest.fixture(name='tokens')
def fixture_ethereum_tokens(ethereum_inquirer, database, inquirer):  # pylint: disable=unused-argument
    from rotkehlchen.chain.ethereum.tokens import EthereumTokens

    return EthereumTokens(database, ethereum_inquirer)


def test_truncated_token_response_is_a_failure_not_empty_coverage(tokens) -> None:
    """A shorter tokensBalance result must not be read as "all those tokens are zero"."""
    queried = [
        EvmTokenDetectionData(
            identifier=f'eip155:1/erc20:0x{i:040x}',
            address=make_evm_address(),
            decimals=18,
        ) for i in range(1, 3)
    ]
    with (
        patch('rotkehlchen.chain.evm.contracts.EvmContract.call', return_value=[0]),
        pytest.raises(RemoteError),
    ):
        tokens.get_token_balances(address=make_evm_address(), tokens=queried, call_order=[])


def test_one_address_can_be_eligible_while_another_is_pending(database) -> None:
    now = ts_now()
    _sync(database, TEST_ADDR1, end=now)
    _observe(database, TEST_ADDR1, A_ETH.identifier, '3', now)
    _observe(database, TEST_ADDR2, A_ETH.identifier, '3', now)  # queried, but never synced

    assert CurrentBalanceMismatchDetector(database=database).run() == 1
    with database.conn.read_ctx() as cursor:
        checks = get_balance_checks(cursor)
    assert list(checks) == [(LOCATION_ETHEREUM, TEST_ADDR1, A_ETH.identifier)]

    pending = get_wallet_evidence(
        database=database,
        location=LOCATION_ETHEREUM,
        address=TEST_ADDR2,
        asset=A_ETH.identifier,
        derived=None,
    )
    assert BucketReason.HISTORY_NOT_SYNCED in pending.pending_reasons


def test_pending_decoding_only_blocks_the_mapped_address(database) -> None:
    for address in (TEST_ADDR1, TEST_ADDR2):
        _sync(database, address, end=(now := ts_now()))
        _observe(database, address, A_ETH.identifier, '0', now)

    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO evm_transactions(identifier, tx_hash, chain_id, timestamp, block_number, '
            'from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce) '
            'VALUES (1, ?, ?, ?, 1, ?, ?, "0", "21000", "1", "21000", "", 0)',
            (
                make_evm_tx_hash(),
                SupportedBlockchain.ETHEREUM.to_chain_id().serialize_for_db(),
                now, TEST_ADDR2, TEST_ADDR2,
            ),
        )
        write_cursor.execute(
            'INSERT INTO evmtx_address_mappings(tx_id, address) VALUES (1, ?)',
            (TEST_ADDR2,),
        )

    assert CurrentBalanceMismatchDetector(database=database).run() == 1
    with database.conn.read_ctx() as cursor:
        checks = get_balance_checks(cursor)
    assert list(checks) == [(LOCATION_ETHEREUM, TEST_ADDR1, A_ETH.identifier)]
    check = checks[LOCATION_ETHEREUM, TEST_ADDR1, A_ETH.identifier]
    assert check.derived_balance == check.observed_balance == FVal(0)

    pending = get_wallet_evidence(
        database=database,
        location=LOCATION_ETHEREUM,
        address=TEST_ADDR2,
        asset=A_ETH.identifier,
        derived=None,
    )
    assert pending.pending_reasons == (BucketReason.HISTORY_PENDING_DECODING,)


def test_swapped_identity_invalidates_saved_match_without_processing(database) -> None:
    """A changed asset identity stops trusting old evidence immediately, before reprocessing."""
    from rotkehlchen.globaldb.handler import GlobalDBHandler

    address = TEST_ADDR1
    now = ts_now()
    _sync(database, address, end=now)
    _observe(database, address, A_ETH.identifier, '1', now)
    observation = get_wallet_observations(database)[LOCATION_ETHEREUM, address, A_ETH.identifier]
    derived = DerivedSnapshot(balance=FVal(1), latest_event_identifier=None)
    with database.user_write() as write_cursor:
        save_balance_check(write_cursor, BucketBalanceCheck(
            location=LOCATION_ETHEREUM,
            location_label=address,
            asset=A_ETH.identifier,
            derived_balance=FVal(1),
            observed_balance=FVal(1),
            latest_event_identifier=None,
            observed_at=observation.observed_at,
            compared_at=Timestamp(now),
            observation_id=observation.observation_id,
        ))

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute(
            "UPDATE common_asset_details SET swapped_for='BTC' WHERE identifier=?",
            (A_ETH.identifier,),
        )

    evidence = get_wallet_evidence(
        database=database,
        location=LOCATION_ETHEREUM,
        address=address,
        asset=A_ETH.identifier,
        derived=derived,
    )
    assert evidence.amount is None  # the old identity's observation is not evidence anymore
    assert BucketReason.DERIVED_SNAPSHOT_CHANGED in evidence.pending_reasons
    with database.conn.read_ctx() as cursor:
        check = get_balance_checks(cursor)[LOCATION_ETHEREUM, address, A_ETH.identifier]

    classification = classify_bucket(
        is_blocked=False,
        unsupported=evidence.unsupported,
        check=check,
        derived=evidence.derived_snapshot,
        is_derived_history_stale=False,
        latest_observed_at=evidence.observed_at,
        latest_observation_id=evidence.observation_id,
        now=Timestamp(now),
        tolerance=FVal('0.001'),
        pending_reasons=evidence.pending_reasons,
    )
    assert classification.status == BucketStatus.PENDING
    assert BucketReason.DERIVED_SNAPSHOT_CHANGED in classification.reasons
    assert CurrentBalanceMismatchDetector(database=database).run() == 0
    with database.conn.read_ctx() as cursor:
        assert get_balance_checks(cursor)[LOCATION_ETHEREUM, address, A_ETH.identifier] == check
