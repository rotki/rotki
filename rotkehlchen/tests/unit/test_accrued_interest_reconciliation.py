from typing import TYPE_CHECKING

import pytest
from eth_utils import keccak, to_canonical_address

from rotkehlchen.assets.types import AssetFlag
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V2, CPT_AAVE_V3, MINT
from rotkehlchen.chain.evm.decoding.aave.v3.constants import BURN
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.constants import ZERO
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.data_issues.bucket_checks import (
    BucketReason,
    BucketStatus,
    DerivedSnapshot,
    get_balance_checks,
)
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.detectors.current_balance import (
    CurrentBalanceMismatchDetector,
)
from rotkehlchen.history.data_issues.diagnostics import explain_data_issue
from rotkehlchen.history.data_issues.eligibility import get_wallet_evidence
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.reconciliation import get_reconciliation_report
from rotkehlchen.history.data_issues.types import DataIssueFilters
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.reconciliation import (
    add_complete_sync,
    add_observation,
    clear_stale_marker,
)
from rotkehlchen.types import (
    ChainID,
    EventMetricKey,
    EvmTransaction,
    Timestamp,
    TokenKind,
)
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms

pytestmark = [
    pytest.mark.accounting_update,
    pytest.mark.parametrize('use_clean_caching_directory', [True]),
    pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]]),
]

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress

RAY = 10 ** 27
TOLERANCE = FVal('0.005')


def _create_token(
        database: DBHandler,
        symbol: str,
        protocol: str | None,
        flag: AssetFlag | None = None,
) -> EvmToken:
    token = get_or_create_evm_token(
        userdb=database,
        evm_address=make_evm_address(),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        decimals=6,
        name=symbol,
        symbol=symbol,
        protocol=protocol,
    )
    if flag is not None:
        GlobalDBHandler.set_asset_flag(token.identifier, flag, enabled=True)
    return token


def _topic_addr(address: str) -> str:
    return '0x' + (b'\x00' * 12 + to_canonical_address(address)).hex()


def _scaled_log_data(value: int, balance_increase: int, index: int) -> str:
    return '0x' + (
        value.to_bytes(32) +
        balance_increase.to_bytes(32) +
        index.to_bytes(32)
    ).hex()


def _add_evm_balance_event_with_logs(
        database: DBHandler,
        address: ChecksumEvmAddress,
        token: EvmToken,
        derived_balance: str,
        ts_sec: int,
        logs: list[dict] | None = None,
        sort_key: int = 1,
        manual: bool = False,
) -> int:
    """Insert an event, its latest balance metric, and optional decoded EVM receipt logs."""
    tx_hash = make_evm_tx_hash()
    ts_ms = ts_sec_to_ms(Timestamp(ts_sec))
    with database.user_write() as write_cursor:
        event = (
            HistoryEvent(
                group_identifier=f'manual-{bytes(tx_hash).hex()}',
                sequence_index=0,
                timestamp=ts_ms,
                location=LOCATION_ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=token,
                amount=FVal(derived_balance),
                location_label=address,
            ) if manual else EvmEvent(
                tx_ref=tx_hash,
                sequence_index=0,
                timestamp=ts_ms,
                location=LOCATION_ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=token,
                amount=FVal(derived_balance),
                location_label=address,
            )
        )
        event_id = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=event,
        )
        assert event_id is not None
        write_cursor.execute(
            'INSERT INTO event_metrics(event_identifier, location, location_label, protocol, '
            'metric_key, metric_value, asset, timestamp, sequence_index, sort_key) '
            'VALUES (?, ?, ?, NULL, ?, ?, ?, ?, 0, ?)',
            (
                event_id,
                LOCATION_ETHEREUM,
                address,
                EventMetricKey.BALANCE.serialize(),
                derived_balance,
                token.identifier,
                ts_ms,
                sort_key,
            ),
        )
        if not manual and logs is not None:
            dbevmtx = DBEvmTx(database)
            dbevmtx.add_transactions(
                write_cursor=write_cursor,
                evm_transactions=[EvmTransaction(
                    tx_hash=tx_hash,
                    chain_id=ChainID.ETHEREUM,
                    timestamp=Timestamp(ts_sec),
                    block_number=20_000_000 + sort_key,
                    from_address=address,
                    to_address=token.evm_address,
                    value=0,
                    gas=100_000,
                    gas_price=1,
                    gas_used=50_000,
                    input_data=b'',
                    nonce=sort_key,
                )],
                relevant_address=address,
            )
            tx_db_id = dbevmtx.add_or_ignore_receipt_data(
                write_cursor=write_cursor,
                chain_id=ChainID.ETHEREUM,
                data={
                    'transactionHash': str(tx_hash),
                    'contractAddress': None,
                    'status': 1,
                    'type': '0x2',
                    'logs': logs,
                },
            )
            write_cursor.execute(
                'INSERT OR IGNORE INTO evm_tx_mappings(tx_id, value) VALUES (?, ?)',
                (tx_db_id, TX_DECODED),
            )

    clear_stale_marker(database)
    return event_id


def _mint_log(token: EvmToken, user: str, index: int, log_index: int = 0) -> dict:
    return {
        'logIndex': log_index,
        'address': token.evm_address,
        'topics': ['0x' + MINT.hex(), _topic_addr(TEST_ADDR2), _topic_addr(user)],
        'data': _scaled_log_data(value=100, balance_increase=0, index=index),
    }


def _burn_log(
        token: EvmToken,
        user: str,
        target: str,
        index: int,
        log_index: int = 0,
) -> dict:
    return {
        'logIndex': log_index,
        'address': token.evm_address,
        'topics': ['0x' + BURN.hex(), _topic_addr(user), _topic_addr(target)],
        'data': _scaled_log_data(value=50, balance_increase=5, index=index),
    }


def _report_bucket(database: DBHandler, address: str, token: EvmToken, now: Timestamp):
    report = get_reconciliation_report(
        database=database,
        location=LOCATION_ETHEREUM,
        location_label=address,
        now=now,
    )
    return next(b for b in report.entries if b.asset == token.identifier)


def test_aave_v3_debt_and_atoken_reconcile_with_mint_and_burn_logs(rotkehlchen_instance) -> None:
    """Aave v3 variableDebt (Mint topics[2]) and aToken (Burn topics[1] != topics[2]) reconcile."""
    database = rotkehlchen_instance.data.db
    now = ts_now()
    debt = _create_token(database, 'variableDebtEthUSDC', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_DEBT)  # noqa: E501
    atoken = _create_token(database, 'aEthUSDC', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)
    spark_debt = _create_token(database, 'variableDebtDAI', CPT_SPARK, AssetFlag.ACCRUING_INTEREST_DEBT)  # noqa: E501

    # 1. Aave v3 variableDebt: Mint log with another user's log at higher log_index ignored,
    #    and two logs for TEST_ADDR1 where the later log_index wins.
    _add_evm_balance_event_with_logs(
        database=database,
        address=TEST_ADDR1,
        token=debt,
        derived_balance='100',
        ts_sec=now - 3_600,
        logs=[
            _mint_log(debt, TEST_ADDR1, index=RAY, log_index=1),
            _mint_log(debt, TEST_ADDR1, index=RAY * 102 // 100, log_index=2),
            _mint_log(debt, TEST_ADDR2, index=RAY * 150 // 100, log_index=3),
        ],
    )
    # 2. Aave v3 aToken: Burn log where from (topics[1]) == user and target (topics[2]) != user
    _add_evm_balance_event_with_logs(
        database=database,
        address=TEST_ADDR1,
        token=atoken,
        derived_balance='200',
        ts_sec=now - 3_600,
        logs=[_burn_log(atoken, user=TEST_ADDR1, target=TEST_ADDR2, index=RAY, log_index=0)],
    )
    # 3. Spark Lend variableDebt: Burn log where topics[1] == user and topics[2] == ZERO_ADDRESS
    _add_evm_balance_event_with_logs(
        database=database,
        address=TEST_ADDR1,
        token=spark_debt,
        derived_balance='50',
        ts_sec=now - 3_600,
        logs=[_burn_log(spark_debt, user=TEST_ADDR1, target=ZERO_ADDRESS, index=RAY, log_index=0)],
    )
    add_complete_sync(database, TEST_ADDR1, now)
    add_observation(database, TEST_ADDR1, debt, '105', now - 60, observation_index=RAY * 1071 // 1000)  # noqa: E501
    add_observation(database, TEST_ADDR1, atoken, '205', now - 60, observation_index=RAY * 1025 // 1000)  # noqa: E501
    add_observation(database, TEST_ADDR1, spark_debt, '55', now - 60, observation_index=RAY * 110 // 100)  # noqa: E501

    compared = CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run()
    assert compared == 3

    for token, expected_derived, expected_interest, expected_observed in (
        (debt, FVal('100'), FVal('5'), FVal('105')),
        (atoken, FVal('200'), FVal('5'), FVal('205')),
        (spark_debt, FVal('50'), FVal('5'), FVal('55')),
    ):
        bucket = _report_bucket(database, TEST_ADDR1, token, now)
        assert bucket.status == BucketStatus.RECONCILED
        assert bucket.reasons == ()
        assert bucket.check is not None
        assert bucket.check.derived_balance == expected_derived
        assert bucket.check.accrued_interest == expected_interest
        assert bucket.check.observed_balance == expected_observed
        assert bucket.delta == ZERO

    assert DataIssuesManager(database).list_issues(
        DataIssueFilters(kind=IssueKind.CURRENT_BALANCE_MISMATCH.value),
    ) == []


def test_real_missing_history_mismatch_preserves_unexplained_delta(rotkehlchen_instance) -> None:
    """Missing borrow/supply stays detectable; delta reflects only unexplained difference."""
    database = rotkehlchen_instance.data.db
    now = ts_now()
    debt = _create_token(database, 'variableDebtEthUSDC', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_DEBT)  # noqa: E501

    _add_evm_balance_event_with_logs(
        database=database,
        address=TEST_ADDR1,
        token=debt,
        derived_balance='100',
        ts_sec=now - 3_600,
        logs=[_mint_log(debt, TEST_ADDR1, index=RAY)],
    )
    add_complete_sync(database, TEST_ADDR1, now)
    # 5 accrued interest + 50 missing borrow -> observed=155, unexplained delta=+50
    add_observation(
        database, TEST_ADDR1, debt, '155', now - 60, observation_index=RAY * 105 // 100,
    )

    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    bucket = _report_bucket(database, TEST_ADDR1, debt, now)
    assert bucket.status == BucketStatus.MISMATCH
    assert bucket.check is not None
    assert bucket.check.derived_balance == FVal('100')
    assert bucket.check.accrued_interest == FVal('5')
    assert bucket.check.observed_balance == FVal('155')
    assert bucket.delta == FVal('50')

    issues = DataIssuesManager(database).list_issues(
        DataIssueFilters(kind=IssueKind.CURRENT_BALANCE_MISMATCH.value),
    )
    assert len(issues) == 1
    assert issues[0].payload['derived_balance'] == '100'
    assert issues[0].payload['accrued_interest'] == '5'
    assert issues[0].payload['observed_balance'] == '155'
    assert issues[0].payload['delta'] == '50'
    explanation = explain_data_issue(database=database, issue_id=issues[0].id)
    assert explanation['facts']['accrued_interest'] == '5'

    # Also test observed between derived and expected (derived=100, accrued=10, obs=102 -> -8)
    add_observation(
        database, TEST_ADDR1, debt, '102', now - 30, observation_index=RAY * 110 // 100,
    )
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    bucket = _report_bucket(database, TEST_ADDR1, debt, now)
    assert bucket.status == BucketStatus.MISMATCH
    assert bucket.check is not None
    assert bucket.check.accrued_interest == FVal('10')
    assert bucket.delta == FVal('-8')


def test_no_double_counting_when_later_event_books_interest(rotkehlchen_instance) -> None:
    """Booking interest in a later tx invalidates the old check and anchors to the new index."""
    database = rotkehlchen_instance.data.db
    now = ts_now()
    debt = _create_token(database, 'variableDebtEthUSDC', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_DEBT)  # noqa: E501

    _add_evm_balance_event_with_logs(
        database=database,
        address=TEST_ADDR1,
        token=debt,
        derived_balance='100',
        ts_sec=now - 7_200,
        logs=[_mint_log(debt, TEST_ADDR1, index=RAY)],
        sort_key=1,
    )
    add_complete_sync(database, TEST_ADDR1, now)
    add_observation(database, TEST_ADDR1, debt, '105', now - 3_600, observation_index=RAY * 105 // 100)  # noqa: E501

    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    first = _report_bucket(database, TEST_ADDR1, debt, now)
    assert first.status == BucketStatus.RECONCILED
    assert first.check is not None
    assert first.check.derived_balance == FVal('100')
    assert first.check.accrued_interest == FVal('5')

    # Later tx books the 5 accrued interest + 50 new borrow -> derived=155 at I_last=1.05e27
    _add_evm_balance_event_with_logs(
        database=database,
        address=TEST_ADDR1,
        token=debt,
        derived_balance='155',
        ts_sec=now - 1_800,
        logs=[_mint_log(debt, TEST_ADDR1, index=RAY * 105 // 100)],
        sort_key=2,
    )
    # Before detector reruns, old check is invalidated via DERIVED_SNAPSHOT_CHANGED
    stale_bucket = _report_bucket(database, TEST_ADDR1, debt, now)
    assert stale_bucket.status == BucketStatus.PENDING
    assert BucketReason.DERIVED_SNAPSHOT_CHANGED in stale_bucket.reasons

    # Fresh observation at I_obs=1.071e27 (2% further growth on 155 = +3.1 -> 158.1)
    add_observation(database, TEST_ADDR1, debt, '158.1', now - 60, observation_index=RAY * 1071 // 1000)  # noqa: E501
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    second = _report_bucket(database, TEST_ADDR1, debt, now)
    assert second.status == BucketStatus.RECONCILED
    assert second.check is not None
    assert second.check.derived_balance == FVal('155')
    assert second.check.accrued_interest == FVal('3.1')  # NOT 5 + 3.1
    assert second.delta == ZERO


def test_zero_balance_and_zeroed_onchain_shortcuts(rotkehlchen_instance) -> None:
    """Zero derived reconciles without index; zeroed on-chain without index reports MISMATCH."""
    database = rotkehlchen_instance.data.db
    now = ts_now()
    closed = _create_token(database, 'variableDebtEthDAI', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_DEBT)  # noqa: E501
    unexpected = _create_token(database, 'aEthWBTC', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501
    zeroed_no_idx = _create_token(database, 'aEthLINK', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501
    zeroed_with_idx = _create_token(database, 'aEthUSDT', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501

    # 1. Closed position: derived=0, observed=0, no receipt log, no observation_index -> RECONCILED
    _add_evm_balance_event_with_logs(database, TEST_ADDR1, closed, '0', now - 3_600, logs=None)
    # 2. Zero derived with non-zero on-chain balance (no index) -> MISMATCH
    _add_evm_balance_event_with_logs(database, TEST_ADDR1, unexpected, '0', now - 3_600, logs=None)
    # 3. Derived > 0, observed == 0, observation_index=None -> immediate MISMATCH
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, zeroed_no_idx, '100', now - 3_600,
        logs=[_mint_log(zeroed_no_idx, TEST_ADDR1, index=RAY)],
    )
    # 4. Derived > 0, observed == 0, observation_index present -> MISMATCH with accrued_interest
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, zeroed_with_idx, '100', now - 3_600,
        logs=[_mint_log(zeroed_with_idx, TEST_ADDR1, index=RAY)],
    )
    add_complete_sync(database, TEST_ADDR1, now)
    add_observation(database, TEST_ADDR1, closed, '0', now - 60, observation_index=None)
    add_observation(database, TEST_ADDR1, unexpected, '10', now - 60, observation_index=None)
    add_observation(database, TEST_ADDR1, zeroed_no_idx, '0', now - 60, observation_index=None)
    add_observation(database, TEST_ADDR1, zeroed_with_idx, '0', now - 60, observation_index=RAY * 105 // 100)  # noqa: E501

    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 4

    closed_b = _report_bucket(database, TEST_ADDR1, closed, now)
    assert closed_b.status == BucketStatus.RECONCILED
    assert closed_b.check is not None
    assert closed_b.check.accrued_interest == ZERO
    assert closed_b.delta == ZERO

    unexpected_b = _report_bucket(database, TEST_ADDR1, unexpected, now)
    assert unexpected_b.status == BucketStatus.MISMATCH
    assert unexpected_b.delta == FVal('10')

    zeroed_no_idx_b = _report_bucket(database, TEST_ADDR1, zeroed_no_idx, now)
    assert zeroed_no_idx_b.status == BucketStatus.MISMATCH
    assert zeroed_no_idx_b.check is not None
    assert zeroed_no_idx_b.check.accrued_interest is None
    assert zeroed_no_idx_b.delta == FVal('-100')

    zeroed_with_idx_b = _report_bucket(database, TEST_ADDR1, zeroed_with_idx, now)
    assert zeroed_with_idx_b.status == BucketStatus.MISMATCH
    assert zeroed_with_idx_b.check is not None
    assert zeroed_with_idx_b.check.accrued_interest == FVal('5')
    assert zeroed_with_idx_b.delta == FVal('-105')


def test_missing_index_anchor_stale_index_rebasing_and_spark_savings(rotkehlchen_instance) -> None:
    """Missing index/anchor/manual/BalanceTransfer -> PENDING; Aave v2 -> NOT_COMPARED; sDAI -> standard."""  # noqa: E501
    database = rotkehlchen_instance.data.db
    now = ts_now()

    missing_idx = _create_token(database, 'aEthWETH', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501
    manual_evt = _create_token(database, 'aEthGHO', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501
    plain_transfer = _create_token(database, 'aEthLUSD', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501
    stale_idx = _create_token(database, 'aEthFRAX', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501
    aave_v2 = _create_token(database, 'aUSDC', CPT_AAVE_V2, AssetFlag.REBASING)
    stable_debt = _create_token(database, 'stableDebtEthUSDC', CPT_AAVE_V3, AssetFlag.REBASING)
    sdai = _create_token(database, 'sDAI', CPT_SPARK, flag=None)  # ERC-4626, NOT accruing

    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, missing_idx, '100', now - 3_600,
        logs=[_mint_log(missing_idx, TEST_ADDR1, index=RAY)],
    )
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, manual_evt, '100', now - 3_600, manual=True,
    )
    # Plain aToken transfer has no Mint/Burn log (only e.g. ERC-20 Transfer / BalanceTransfer)
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, plain_transfer, '100', now - 3_600, logs=[],
    )
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, stale_idx, '100', now - 3_600,
        logs=[_mint_log(stale_idx, TEST_ADDR1, index=RAY * 105 // 100)],
    )
    _add_evm_balance_event_with_logs(database, TEST_ADDR1, aave_v2, '100', now - 3_600, logs=[])
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, stable_debt, '100', now - 3_600, logs=[],
    )
    _add_evm_balance_event_with_logs(database, TEST_ADDR1, sdai, '100', now - 3_600, logs=[])

    add_complete_sync(database, TEST_ADDR1, now)
    add_observation(database, TEST_ADDR1, missing_idx, '105', now - 60, observation_index=None)
    add_observation(database, TEST_ADDR1, manual_evt, '105', now - 60, observation_index=RAY * 105 // 100)  # noqa: E501
    add_observation(database, TEST_ADDR1, plain_transfer, '105', now - 60, observation_index=RAY * 105 // 100)  # noqa: E501
    add_observation(database, TEST_ADDR1, stale_idx, '100', now - 60, observation_index=RAY * 104 // 100)  # noqa: E501
    add_observation(database, TEST_ADDR1, aave_v2, '105', now - 60, observation_index=None)
    add_observation(database, TEST_ADDR1, stable_debt, '105', now - 60, observation_index=None)
    add_observation(database, TEST_ADDR1, sdai, '100', now - 60, observation_index=None)

    # Only sDAI should be compared (standard reconciliation without observation_index)
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1

    b_missing = _report_bucket(database, TEST_ADDR1, missing_idx, now)
    assert b_missing.status == BucketStatus.PENDING
    assert BucketReason.INTEREST_INDEX_MISSING in b_missing.reasons

    b_manual = _report_bucket(database, TEST_ADDR1, manual_evt, now)
    assert b_manual.status == BucketStatus.PENDING
    assert BucketReason.INTEREST_ANCHOR_UNAVAILABLE in b_manual.reasons

    b_transfer = _report_bucket(database, TEST_ADDR1, plain_transfer, now)
    assert b_transfer.status == BucketStatus.PENDING
    assert BucketReason.INTEREST_ANCHOR_UNAVAILABLE in b_transfer.reasons

    b_stale = _report_bucket(database, TEST_ADDR1, stale_idx, now)
    assert b_stale.status == BucketStatus.PENDING
    assert BucketReason.OBSERVATION_STALE in b_stale.reasons

    for rebasing_token in (aave_v2, stable_debt):
        b_rebasing = _report_bucket(database, TEST_ADDR1, rebasing_token, now)
        assert b_rebasing.status == BucketStatus.NOT_COMPARED
        assert BucketReason.REBASING in b_rebasing.reasons

    b_sdai = _report_bucket(database, TEST_ADDR1, sdai, now)
    assert b_sdai.status == BucketStatus.RECONCILED
    assert b_sdai.check is not None
    assert b_sdai.check.accrued_interest is None
    assert b_sdai.delta == ZERO


def test_saved_check_without_accrued_interest_invalidates_after_flag_enabled(
        rotkehlchen_instance,
) -> None:
    """A check & open mismatch saved before flagging becomes PENDING and auto-resolves on rerun."""
    database = rotkehlchen_instance.data.db
    now = ts_now()
    token = _create_token(database, 'aEthCRV', CPT_AAVE_V3, flag=None)
    event_id = _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, token, '100', now - 3_600,
        logs=[_mint_log(token, TEST_ADDR1, index=RAY)],
    )
    add_complete_sync(database, TEST_ADDR1, now)
    add_observation(
        database, TEST_ADDR1, token, '105', now - 60, observation_index=RAY * 105 // 100,
    )

    # Before flag: detector writes check with accrued_interest=None and opens a MISMATCH issue
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    before_bucket = _report_bucket(database, TEST_ADDR1, token, now)
    assert before_bucket.status == BucketStatus.MISMATCH
    assert before_bucket.check is not None
    assert before_bucket.check.accrued_interest is None
    issues_manager = DataIssuesManager(database)
    open_before = issues_manager.list_issues(
        DataIssueFilters(
            kind=IssueKind.CURRENT_BALANCE_MISMATCH.value,
            state=IssueState.OPEN.value,
        ),
    )
    assert len(open_before) == 1
    assert 'accrued_interest' not in open_before[0].payload

    # Once flagged as accruing: old check (accrued_interest=None) is stale -> PENDING
    GlobalDBHandler.set_asset_flag(token.identifier, AssetFlag.ACCRUING_INTEREST_SUPPLY, enabled=True)  # noqa: E501
    pending = _report_bucket(database, TEST_ADDR1, token, now)
    assert pending.status == BucketStatus.PENDING
    assert BucketReason.DERIVED_SNAPSHOT_CHANGED in pending.reasons

    # Fresh single-bucket evidence also sees observation_index and accrued_interest
    fresh = get_wallet_evidence(
        database=database,
        location=LOCATION_ETHEREUM,
        address=TEST_ADDR1,
        asset=token.identifier,
        derived=DerivedSnapshot(
            balance=FVal('100'),
            latest_event_identifier=event_id,
            latest_ts=ts_sec_to_ms(Timestamp(now - 3_600)),
        ),
    )
    assert fresh.observation_index == RAY * 105 // 100
    assert fresh.accrued_interest == FVal('5')

    # Re-running detector recomputes check with accrued_interest=5, reconciles, and resolves issue
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    reconciled = _report_bucket(database, TEST_ADDR1, token, now)
    assert reconciled.status == BucketStatus.RECONCILED
    with database.conn.read_ctx() as cursor:
        saved = get_balance_checks(cursor)[LOCATION_ETHEREUM, TEST_ADDR1, token.identifier]
    assert saved.accrued_interest == FVal('5')
    assert issues_manager.list_issues(
        DataIssueFilters(
            kind=IssueKind.CURRENT_BALANCE_MISMATCH.value,
            state=IssueState.OPEN.value,
        ),
    ) == []
    resolved_after = issues_manager.list_issues(
        DataIssueFilters(
            kind=IssueKind.CURRENT_BALANCE_MISMATCH.value,
            state=IssueState.RESOLVED.value,
        ),
    )
    assert len(resolved_after) == 1
    assert resolved_after[0].id == open_before[0].id


def test_routine_balance_refresh_emits_only_observation_superseded(rotkehlchen_instance) -> None:
    """A newer observation with grown index emits OBSERVATION_SUPERSEDED, not DERIVED_SNAPSHOT_CHANGED."""  # noqa: E501
    database = rotkehlchen_instance.data.db
    now = ts_now()
    token = _create_token(database, 'aEthUNI', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)

    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, token, '100', now - 7_200,
        logs=[_mint_log(token, TEST_ADDR1, index=RAY)],
        sort_key=1,
    )
    add_complete_sync(database, TEST_ADDR1, now)
    add_observation(
        database, TEST_ADDR1, token, '105', now - 3_600, observation_index=RAY * 105 // 100,
    )
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    assert _report_bucket(database, TEST_ADDR1, token, now).status == BucketStatus.RECONCILED

    # Routine balance refresh: newer observation with grown index, unchanged derived history
    add_observation(
        database, TEST_ADDR1, token, '106', now - 60, observation_index=RAY * 106 // 100,
    )
    refreshed = _report_bucket(database, TEST_ADDR1, token, now)
    assert refreshed.status == BucketStatus.PENDING
    assert BucketReason.OBSERVATION_SUPERSEDED in refreshed.reasons
    assert BucketReason.DERIVED_SNAPSHOT_CHANGED not in refreshed.reasons

    # If derived history ALSO changes, both reasons are reported
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, token, '150', now - 1_800,
        logs=[_mint_log(token, TEST_ADDR1, index=RAY * 105 // 100)],
        sort_key=2,
    )
    both = _report_bucket(database, TEST_ADDR1, token, now)
    assert both.status == BucketStatus.PENDING
    assert BucketReason.OBSERVATION_SUPERSEDED in both.reasons
    assert BucketReason.DERIVED_SNAPSHOT_CHANGED in both.reasons


def test_zeroed_onchain_with_index_but_unavailable_anchor_reports_mismatch(
        rotkehlchen_instance,
) -> None:
    """derived > 0, observed == 0, observation_index > 0, and missing I_last reports MISMATCH."""
    database = rotkehlchen_instance.data.db
    now = ts_now()
    manual_zeroed = _create_token(database, 'aEthSNX', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501
    transfer_zeroed = _create_token(database, 'aEthBAL', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501

    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, manual_zeroed, '100', now - 3_600, manual=True,
    )
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, transfer_zeroed, '100', now - 3_600, logs=[],
    )
    add_complete_sync(database, TEST_ADDR1, now)
    add_observation(
        database, TEST_ADDR1, manual_zeroed, '0', now - 60, observation_index=RAY * 105 // 100,
    )
    add_observation(
        database, TEST_ADDR1, transfer_zeroed, '0', now - 60, observation_index=RAY * 105 // 100,
    )

    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 2
    for token in (manual_zeroed, transfer_zeroed):
        bucket = _report_bucket(database, TEST_ADDR1, token, now)
        assert bucket.status == BucketStatus.MISMATCH
        assert bucket.check is not None
        assert bucket.check.accrued_interest is None
        assert bucket.delta == FVal('-100')


def test_malformed_zero_index_and_balance_transfer_logs_become_anchor_unavailable(
        rotkehlchen_instance,
) -> None:
    """Short log data, zero index, or BalanceTransfer + other user's Mint -> anchor unavailable."""
    database = rotkehlchen_instance.data.db
    now = ts_now()
    short_data_tok = _create_token(database, 'aEthENS', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501
    zero_index_tok = _create_token(database, 'aEthMKR', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501
    bal_transfer_tok = _create_token(database, 'aEthRPL', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)  # noqa: E501

    # 1. Mint log with truncated data (64 bytes < 96)
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, short_data_tok, '100', now - 3_600,
        logs=[{
            'logIndex': 0,
            'address': short_data_tok.evm_address,
            'topics': ['0x' + MINT.hex(), _topic_addr(TEST_ADDR2), _topic_addr(TEST_ADDR1)],
            'data': '0x' + (100).to_bytes(32).hex() + (0).to_bytes(32).hex(),
        }],
    )
    # 2. Mint log with index == 0
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, zero_index_tok, '100', now - 3_600,
        logs=[_mint_log(zero_index_tok, TEST_ADDR1, index=0)],
    )
    # 3. Tx with another user's Mint log AND a BalanceTransfer log for TEST_ADDR1
    balance_transfer_topic = '0x' + keccak(
        text='BalanceTransfer(address,address,uint256,uint256)',
    ).hex()
    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, bal_transfer_tok, '100', now - 3_600,
        logs=[
            _mint_log(bal_transfer_tok, TEST_ADDR2, index=RAY, log_index=0),
            {
                'logIndex': 1,
                'address': bal_transfer_tok.evm_address,
                'topics': [balance_transfer_topic, _topic_addr(TEST_ADDR2), _topic_addr(TEST_ADDR1)],  # noqa: E501
                'data': '0x' + (100).to_bytes(32).hex() + RAY.to_bytes(32).hex(),
            },
        ],
    )
    add_complete_sync(database, TEST_ADDR1, now)
    for token in (short_data_tok, zero_index_tok, bal_transfer_tok):
        add_observation(
            database, TEST_ADDR1, token, '105', now - 60, observation_index=RAY * 105 // 100,
        )

    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 0
    for token in (short_data_tok, zero_index_tok, bal_transfer_tok):
        bucket = _report_bucket(database, TEST_ADDR1, token, now)
        assert bucket.status == BucketStatus.PENDING
        assert BucketReason.INTEREST_ANCHOR_UNAVAILABLE in bucket.reasons


def test_unflagging_accruing_token_clears_accrued_interest_on_check_and_issue(
        rotkehlchen_instance,
) -> None:
    """Disabling an accruing flag invalidates the saved check and clears accrued_interest."""
    database = rotkehlchen_instance.data.db
    now = ts_now()
    token = _create_token(database, 'aEthLDO', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)

    _add_evm_balance_event_with_logs(
        database, TEST_ADDR1, token, '100', now - 3_600,
        logs=[_mint_log(token, TEST_ADDR1, index=RAY)],
    )
    add_complete_sync(database, TEST_ADDR1, now)
    add_observation(
        database, TEST_ADDR1, token, '155', now - 60, observation_index=RAY * 105 // 100,
    )

    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    before = _report_bucket(database, TEST_ADDR1, token, now)
    assert before.status == BucketStatus.MISMATCH
    assert before.check is not None
    assert before.check.accrued_interest == FVal('5')
    assert before.delta == FVal('50')
    issues_manager = DataIssuesManager(database)
    issues_before = issues_manager.list_issues(
        DataIssueFilters(kind=IssueKind.CURRENT_BALANCE_MISMATCH.value),
    )
    assert len(issues_before) == 1
    assert issues_before[0].payload['accrued_interest'] == '5'
    assert issues_before[0].payload['delta'] == '50'

    # Unflag the token: saved check (accrued_interest=5 != expected None) becomes PENDING
    GlobalDBHandler.set_asset_flag(token.identifier, AssetFlag.ACCRUING_INTEREST_SUPPLY, enabled=False)  # noqa: E501
    pending = _report_bucket(database, TEST_ADDR1, token, now)
    assert pending.status == BucketStatus.PENDING
    assert BucketReason.DERIVED_SNAPSHOT_CHANGED in pending.reasons

    # Rerunning detector clears accrued_interest on both check and issue payload
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    after = _report_bucket(database, TEST_ADDR1, token, now)
    assert after.status == BucketStatus.MISMATCH
    assert after.check is not None
    assert after.check.accrued_interest is None
    assert after.delta == FVal('55')
    issues_after = issues_manager.list_issues(
        DataIssueFilters(kind=IssueKind.CURRENT_BALANCE_MISMATCH.value),
    )
    assert len(issues_after) == 1
    assert 'accrued_interest' not in issues_after[0].payload
    assert issues_after[0].payload['delta'] == '55'


def test_verified_history_free_accruing_token_reports_mismatch_without_index(
        rotkehlchen_instance,
) -> None:
    """An accruing token with verified zero history reports MISMATCH without an index."""
    database = rotkehlchen_instance.data.db
    now = ts_now()
    token = _create_token(database, 'aEth1INCH', CPT_AAVE_V3, AssetFlag.ACCRUING_INTEREST_SUPPLY)

    add_complete_sync(database, TEST_ADDR1, now)
    add_observation(database, TEST_ADDR1, token, '10', now - 60, observation_index=None)

    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    bucket = _report_bucket(database, TEST_ADDR1, token, now)
    assert bucket.status == BucketStatus.MISMATCH
    assert bucket.check is not None
    assert bucket.check.derived_balance == ZERO
    assert bucket.check.accrued_interest == ZERO
    assert bucket.check.observed_balance == FVal('10')
    assert bucket.check.latest_event_identifier is None
    assert bucket.delta == FVal('10')
    issues = DataIssuesManager(database).list_issues(
        DataIssueFilters(kind=IssueKind.CURRENT_BALANCE_MISMATCH.value),
    )
    assert len(issues) == 1
    assert issues[0].payload['derived_balance'] == '0'
    assert issues[0].payload['observed_balance'] == '10'
    assert issues[0].payload['delta'] == '10'
    assert issues[0].payload['latest_event_identifier'] is None
