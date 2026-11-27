"""Shared declarative harness for old-vs-new PnL parity testing.

Runs a declarative `ParityScenario` through both:
1. New pipeline: `process_cost_basis()` + `query_realized_pnl(..., group_by=ASSET)`
2. Legacy pipeline: `Accountant.process_history()`

and produces a 3-level `ParityDiff` (totals, per-asset breakdown, and underlying
legacy `ProcessedAccountingEvent` / new `event_cost_basis` rows).
"""
import itertools
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import MagicMock, patch

from eth_utils import to_checksum_address

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.cost_basis.pnl import RealizedPnlGroupBy, query_realized_pnl
from rotkehlchen.chain.ethereum.modules.aave.v2.accountant import Aavev2Accountant
from rotkehlchen.chain.ethereum.modules.makerdao.accountant import MakerdaoAccountant
from rotkehlchen.chain.ethereum.modules.thegraph.accountant import ThegraphAccountant
from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregator
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.chain.evm.types import ChainID, string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_USD
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    AssetMovementExtraData,
    AssetMovementTransferSubtype,
)
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.chains import EVM_EVMLIKE_LOCATIONS
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tasks.cost_basis import process_cost_basis
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.fixtures.accounting import (
    LAST_ACCOUNTING_RULES_VERSION,
    _ensure_accounting_rules,
    _read_rules_from_file,
)
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import (
    ChecksumEvmAddress,
    CostBasisMethod,
    EVMTxHash,
    Price,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from rotkehlchen.accounting.mixins.event import AccountingEventMixin
    from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
    from rotkehlchen.accounting.types import MissingPrice
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.accounts import BlockchainAccountData
    from rotkehlchen.db.constants import (
        LINKABLE_ACCOUNTING_PROPERTIES,
        LINKABLE_ACCOUNTING_SETTINGS_NAME,
    )
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.locations.types import LocationIdentifier

BASE_TS: Final = 1_700_000_000
UNIX_TS_THRESHOLD: Final = 1_000_000_000
DEFAULT_START_TS: Final = Timestamp(0)
DEFAULT_END_TS: Final = Timestamp(2_000_000_000)

DEFAULT_EVM_ADDRESS: Final[ChecksumEvmAddress] = string_to_evm_address(
    to_checksum_address(TEST_ADDR1),
)
SECOND_EVM_ADDRESS: Final[ChecksumEvmAddress] = string_to_evm_address(
    to_checksum_address(TEST_ADDR2),
)

_GROUP_COUNTER = itertools.count(1)
_DEFAULT_RULES_CACHE: list[tuple[int, list[dict[str, Any]]]] | None = None


def ts(offset: int) -> Timestamp:
    """Convert a relative second offset from `BASE_TS` to a `Timestamp`."""
    return Timestamp(BASE_TS + offset)


def ts_ms(offset: int) -> TimestampMS:
    """Convert a relative second offset from `BASE_TS` to a `TimestampMS`."""
    return TimestampMS((BASE_TS + offset) * 1000)


def to_ts(at: int | Timestamp) -> Timestamp:
    """Normalize either an absolute Unix timestamp or a `BASE_TS` offset to `Timestamp`."""
    return Timestamp(at) if at >= UNIX_TS_THRESHOLD else ts(at)


def to_ts_ms(at: int | Timestamp) -> TimestampMS:
    """Normalize either an absolute Unix timestamp or a `BASE_TS` offset to `TimestampMS`."""
    return ts_sec_to_ms(Timestamp(at)) if at >= UNIX_TS_THRESHOLD else ts_ms(at)


@dataclass(frozen=True)
class RuleSpec:
    """Declarative accounting rule specification applied to `DBAccountingRules`."""
    event_type: HistoryEventType
    event_subtype: HistoryEventSubType = HistoryEventSubType.NONE
    counterparty: str | None = None
    taxable: bool = True
    count_entire_amount_spend: bool = False
    count_cost_basis_pnl: bool = True
    accounting_treatment: TxAccountingTreatment | None = None
    event_ids: Sequence[int] | None = None
    links: Mapping[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME] = field(
        default_factory=dict,
    )
    force_update: bool = True


@dataclass(frozen=True)
class ParityScenario:
    """Declarative specification of an old-vs-new PnL parity test case."""
    id: str
    events: Sequence[HistoryBaseEntry]
    prices: Mapping[tuple[Asset, Timestamp], Price] = field(default_factory=dict)
    start_ts: Timestamp = DEFAULT_START_TS
    end_ts: Timestamp = DEFAULT_END_TS
    default_prices: Mapping[Asset, Price] = field(default_factory=dict)
    pair_prices: Mapping[tuple[Asset, Asset, Timestamp], Price] = field(default_factory=dict)
    method: CostBasisMethod = CostBasisMethod.FIFO
    settings: Mapping[str, Any] = field(default_factory=dict)
    rules: Sequence[RuleSpec] = ()
    use_default_rules: bool = False
    ignored_assets: Sequence[Asset] = ()
    ignored_actions: Sequence[str | HistoryBaseEntry] = ()
    blockchain_accounts: Sequence[BlockchainAccountData] = ()
    use_real_evm_accountants: bool = False
    run_balance_pass: bool = False
    extra_legacy_events: Sequence[AccountingEventMixin] = ()


@dataclass(frozen=True)
class AssetPnlDiff:
    """Per-asset comparison of old vs new realized PnL."""
    asset: str
    old_taxable: FVal
    old_free: FVal
    new_taxable: FVal
    new_free: FVal

    @property
    def taxable_diff(self) -> FVal:
        return self.new_taxable - self.old_taxable

    @property
    def free_diff(self) -> FVal:
        return self.new_free - self.old_free

    def matches(self, tolerance: FVal = ZERO) -> bool:
        return (
            abs(self.taxable_diff) <= tolerance and
            abs(self.free_diff) <= tolerance
        )


@dataclass(frozen=True)
class ParityDiff:
    """3-level diff output from running both legacy and new PnL pipelines."""
    scenario_id: str
    old_taxable: FVal
    old_free: FVal
    new_taxable: FVal
    new_free: FVal
    stale: bool
    old_missing_prices: set[MissingPrice]
    new_unpriced_events: int
    per_asset: dict[str, AssetPnlDiff]
    old_events: list[ProcessedAccountingEvent]
    new_cost_basis_rows: list[dict[str, Any]]
    new_result: dict[str, Any] = field(default_factory=dict)

    @property
    def taxable_diff(self) -> FVal:
        return self.new_taxable - self.old_taxable

    @property
    def free_diff(self) -> FVal:
        return self.new_free - self.old_free

    def format_report(self, tolerance: FVal = ZERO) -> str:
        """Render a human-readable side-by-side table of totals, per-asset diffs, and events."""
        lines = [
            f'=== Parity Report: {self.scenario_id} ===',
            (
                f'stale={self.stale} | '
                f'old_missing_prices={len(self.old_missing_prices)} | '
                f'new_unpriced_events={self.new_unpriced_events}'
            ),
            '',
            'Totals:',
            f'  {"Metric":<10} {"Old":>20} {"New":>20} {"Diff (New-Old)":>20}',
            f'  {"-" * 73}',
            (
                f'  {"taxable":<10} {self.old_taxable!s:>20} '
                f'{self.new_taxable!s:>20} {self.taxable_diff!s:>20}'
            ),
            (
                f'  {"free":<10} {self.old_free!s:>20} '
                f'{self.new_free!s:>20} {self.free_diff!s:>20}'
            ),
            '',
            'Per-asset breakdown:',
            (
                f'  {"Asset":<24} {"Old Tax":>14} {"New Tax":>14} {"Tax Diff":>14} '
                f'{"Old Free":>14} {"New Free":>14} {"Free Diff":>14}'
            ),
            f'  {"-" * 114}',
        ]
        if len(self.per_asset) == 0:
            lines.append('  (no per-asset rows)')
        else:
            lines.extend(
                f'  {asset_id:<24} {diff.old_taxable!s:>14} {diff.new_taxable!s:>14} '
                f'{diff.taxable_diff!s:>14} {diff.old_free!s:>14} '
                f'{diff.new_free!s:>14} {diff.free_diff!s:>14}'
                f'{"" if diff.matches(tolerance) else " <!>"}'
                for asset_id, diff in self.per_asset.items()
            )

        lines.extend(['', f'Legacy processed events ({len(self.old_events)}):'])
        lines.extend(
            f'  ts={ev.timestamp} type={ev.event_type.name} asset={ev.asset.identifier} '
            f'free_amt={ev.free_amount} tax_amt={ev.taxable_amount} price={ev.price} '
            f'pnl=(tax={ev.pnl.taxable}, free={ev.pnl.free}) notes={ev.notes!r}'
            for ev in self.old_events
        )

        lines.extend(['', f'New event_cost_basis rows ({len(self.new_cost_basis_rows)}):'])
        lines.extend(
            f'  id={row["event_identifier"]} group={row["group_identifier"]} '
            f'{row["event_type"]}/{row["event_subtype"]} dir={row["direction"]} '
            f'loc={row["location"]} label={row["location_label"]} proto={row["protocol"]} '
            f'asset={row["asset"]} basis_u={row["basis_per_unit"]} '
            f'proceeds={row["proceeds"]} pnl={row["realized_pnl"]} '
            f'taxfree={row["taxfree_pnl"]} taxable={row["is_taxable"]}'
            for row in self.new_cost_basis_rows
        )

        if self.old_missing_prices:
            lines.extend(['', f'Legacy missing prices ({len(self.old_missing_prices)}):'])
            lines.extend(f'  {mp}' for mp in sorted(self.old_missing_prices, key=str))

        return '\n'.join(lines)

    def assert_parity(self, tolerance: FVal = ZERO) -> None:
        """Assert total taxable, total free, non-stale state, and all per-asset entries match."""
        failures: list[str] = []
        if self.stale is not False:
            failures.append(f'Expected stale=False, got stale={self.stale}')
        if abs(self.taxable_diff) > tolerance:
            failures.append(
                f'Total taxable mismatch: old={self.old_taxable} vs new={self.new_taxable} '
                f'(diff={self.taxable_diff}, tolerance={tolerance})',
            )
        if abs(self.free_diff) > tolerance:
            failures.append(
                f'Total free mismatch: old={self.old_free} vs new={self.new_free} '
                f'(diff={self.free_diff}, tolerance={tolerance})',
            )
        for asset_id, diff in self.per_asset.items():
            if not diff.matches(tolerance):
                failures.append(
                    f'Asset {asset_id} mismatch: '
                    f'old=(tax={diff.old_taxable}, free={diff.old_free}) vs '
                    f'new=(tax={diff.new_taxable}, free={diff.new_free})',
                )
        if failures:
            failure_summary = '\n'.join(f'- {msg}' for msg in failures)
            raise AssertionError(
                f'PnL parity failed for scenario {self.scenario_id!r}:\n'
                f'{failure_summary}\n\n{self.format_report(tolerance=tolerance)}',
            )

    def assert_expected_divergence(
            self,
            *,
            reason: str,
            old_taxable: FVal | str | int,
            new_taxable: FVal | str | int,
            old_free: FVal | str | int = ZERO,
            new_free: FVal | str | int = ZERO,
            tolerance: FVal = ZERO,
            check_not_stale: bool = True,
            per_asset: Mapping[
                str,
                tuple[FVal | str | int, FVal | str | int, FVal | str | int, FVal | str | int],
            ] | None = None,
    ) -> None:
        """Assert exact old and new totals for documented KNOWN_GAP or DELIBERATE_DIVERGENCE cases.

        `per_asset`, when given, maps `asset_identifier -> (old_tax, old_free, new_tax, new_free)`.
        """
        assert reason.strip(), 'Expected divergence reason must be non-empty'
        exp_old_tax = FVal(old_taxable)
        exp_old_free = FVal(old_free)
        exp_new_tax = FVal(new_taxable)
        exp_new_free = FVal(new_free)

        failures: list[str] = []
        if check_not_stale and self.stale is not False:
            failures.append(f'Expected stale=False, got stale={self.stale}')
        if abs(self.old_taxable - exp_old_tax) > tolerance:
            failures.append(f'old_taxable: expected {exp_old_tax}, got {self.old_taxable}')
        if abs(self.old_free - exp_old_free) > tolerance:
            failures.append(f'old_free: expected {exp_old_free}, got {self.old_free}')
        if abs(self.new_taxable - exp_new_tax) > tolerance:
            failures.append(f'new_taxable: expected {exp_new_tax}, got {self.new_taxable}')
        if abs(self.new_free - exp_new_free) > tolerance:
            failures.append(f'new_free: expected {exp_new_free}, got {self.new_free}')

        if per_asset is not None:
            for asset_id, (eo_tax, eo_free, en_tax, en_free) in per_asset.items():
                actual = self.per_asset.get(
                    asset_id,
                    AssetPnlDiff(
                        asset=asset_id,
                        old_taxable=ZERO,
                        old_free=ZERO,
                        new_taxable=ZERO,
                        new_free=ZERO,
                    ),
                )
                checks = (
                    ('old_taxable', actual.old_taxable, FVal(eo_tax)),
                    ('old_free', actual.old_free, FVal(eo_free)),
                    ('new_taxable', actual.new_taxable, FVal(en_tax)),
                    ('new_free', actual.new_free, FVal(en_free)),
                )
                for label, got, expected in checks:
                    if abs(got - expected) > tolerance:
                        failures.append(
                            f'per_asset[{asset_id}].{label}: expected {expected}, got {got}',
                        )

        if failures:
            failure_summary = '\n'.join(f'- {msg}' for msg in failures)
            raise AssertionError(
                f'Expected divergence assertion failed for {self.scenario_id!r} ({reason}):\n'
                f'{failure_summary}\n\n{self.format_report(tolerance=tolerance)}',
            )


def _checksum_evm_addr(addr: str) -> ChecksumEvmAddress:
    return string_to_evm_address(to_checksum_address(addr))


def evm_event(
        at: int | Timestamp,
        amount: str | int | FVal,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
        asset: Asset = A_ETH,
        location: LocationIdentifier = LOCATION_ETHEREUM,
        location_label: ChecksumEvmAddress | str = DEFAULT_EVM_ADDRESS,
        tx_ref: EVMTxHash | None = None,
        sequence_index: int = 0,
        counterparty: str | None = None,
        address: ChecksumEvmAddress | str | None = None,
        extra_data: dict[str, Any] | None = None,
        group_identifier: str | None = None,
        notes: str | None = None,
) -> EvmEvent:
    """Build an `EvmEvent` on any EVM chain with checksummed addresses."""
    return EvmEvent(
        tx_ref=make_evm_tx_hash() if tx_ref is None else tx_ref,
        sequence_index=sequence_index,
        timestamp=to_ts_ms(at),
        location=location,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=asset,
        amount=FVal(amount),
        location_label=_checksum_evm_addr(location_label),
        counterparty=counterparty,
        address=_checksum_evm_addr(address) if address is not None else None,
        extra_data=extra_data,
        group_identifier=group_identifier,
        notes=notes,
    )


def swap_group(
        at: int | Timestamp,
        group_id: str,
        location: LocationIdentifier,
        location_label: str | None,
        spend: tuple[Asset, str | int | FVal],
        receive: tuple[Asset, str | int | FVal],
        fee: tuple[Asset, str | int | FVal] | None = None,
        counterparty: str | None = None,
        tx_ref: EVMTxHash | None = None,
        sequence_offset: int = 0,
        extra_data: dict[str, Any] | None = None,
        fees: Sequence[tuple[Asset, str | int | FVal]] = (),
) -> list[SwapEvent]:
    """Build a grouped SPEND + RECEIVE (+ optional FEE legs) swap.

    Emits `EvmSwapEvent` when targeting an EVM location or when `counterparty` / `tx_ref`
    is provided, and `SwapEvent` otherwise (exchanges, non-EVM chains).
    """
    timestamp_ms = to_ts_ms(at)
    all_fees = ([fee] if fee is not None else []) + list(fees)
    is_evm = location in EVM_EVMLIKE_LOCATIONS or counterparty is not None or tx_ref is not None

    if is_evm:
        resolved_tx_ref = make_evm_tx_hash() if tx_ref is None else tx_ref
        resolved_label = (
            DEFAULT_EVM_ADDRESS
            if location_label is None
            else _checksum_evm_addr(location_label)
        )
        resolved_group_id = group_id or None
        entries: list[SwapEvent] = [
            EvmSwapEvent(
                tx_ref=resolved_tx_ref,
                sequence_index=sequence_offset,
                timestamp=timestamp_ms,
                location=location,
                location_label=resolved_label,
                event_subtype=HistoryEventSubType.SPEND,
                asset=spend[0],
                amount=FVal(spend[1]),
                counterparty=counterparty,
                extra_data=extra_data,
                group_identifier=resolved_group_id,
            ),
            EvmSwapEvent(
                tx_ref=resolved_tx_ref,
                sequence_index=sequence_offset + 1,
                timestamp=timestamp_ms,
                location=location,
                location_label=resolved_label,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=receive[0],
                amount=FVal(receive[1]),
                counterparty=counterparty,
                extra_data=extra_data,
                group_identifier=resolved_group_id,
            ),
        ]
        for idx, (fee_asset, fee_amount) in enumerate(all_fees):
            entries.append(EvmSwapEvent(
                tx_ref=resolved_tx_ref,
                sequence_index=sequence_offset + 2 + idx,
                timestamp=timestamp_ms,
                location=location,
                location_label=resolved_label,
                event_subtype=HistoryEventSubType.FEE,
                asset=fee_asset,
                amount=FVal(fee_amount),
                counterparty=counterparty,
                extra_data=extra_data,
                group_identifier=resolved_group_id,
            ))
        return entries

    entries = [
        SwapEvent(
            timestamp=timestamp_ms,
            location=location,
            location_label=location_label,
            event_subtype=HistoryEventSubType.SPEND,
            asset=spend[0],
            amount=FVal(spend[1]),
            group_identifier=group_id,
            sequence_index=sequence_offset,
            extra_data=extra_data,
        ),
        SwapEvent(
            timestamp=timestamp_ms,
            location=location,
            location_label=location_label,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=receive[0],
            amount=FVal(receive[1]),
            group_identifier=group_id,
            sequence_index=sequence_offset + 1,
            extra_data=extra_data,
        ),
    ]
    for idx, (fee_asset, fee_amount) in enumerate(all_fees):
        entries.append(SwapEvent(
            timestamp=timestamp_ms,
            location=location,
            location_label=location_label,
            event_subtype=HistoryEventSubType.FEE,
            asset=fee_asset,
            amount=FVal(fee_amount),
            group_identifier=group_id,
            sequence_index=sequence_offset + 2 + idx,
            extra_data=extra_data,
        ))
    return entries


def asset_movement(
        at: int | Timestamp,
        location: LocationIdentifier,
        location_label: str | None,
        subtype: AssetMovementTransferSubtype,
        asset: Asset,
        amount: str | int | FVal,
        fee: tuple[Asset, str | int | FVal] | None = None,
        group_id: str | None = None,
        unique_id: str | None = None,
        extra_data: AssetMovementExtraData | None = None,
        notes: str | None = None,
) -> list[AssetMovement]:
    """Build an exchange `AssetMovement` (plus optional paired FEE movement)."""
    timestamp_ms = to_ts_ms(at)
    primary = AssetMovement(
        timestamp=timestamp_ms,
        location=location,
        location_label=location_label,
        event_subtype=subtype,
        asset=asset,
        amount=FVal(amount),
        group_identifier=group_id,
        unique_id=unique_id,
        extra_data=extra_data,
        notes=notes,
    )
    movements = [primary]
    if fee is not None:
        movements.append(AssetMovement(
            timestamp=timestamp_ms,
            location=location,
            location_label=location_label,
            event_subtype=HistoryEventSubType.FEE,
            asset=fee[0],
            amount=FVal(fee[1]),
            group_identifier=primary.group_identifier,
        ))
    return movements


def history_event(
        at: int | Timestamp,
        location: LocationIdentifier,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
        asset: Asset = A_ETH,
        amount: str | int | FVal = ZERO,
        location_label: str | None = None,
        group_identifier: str | None = None,
        sequence_index: int = 0,
        notes: str | None = None,
        extra_data: dict[str, Any] | None = None,
) -> HistoryEvent:
    """Build a generic `HistoryEvent` for non-EVM chains and exchange ledger events."""
    timestamp_ms = to_ts_ms(at)
    resolved_group = (
        group_identifier
        if group_identifier is not None
        else f'{location}-{timestamp_ms}-{sequence_index}-{next(_GROUP_COUNTER)}'
    )
    return HistoryEvent(
        group_identifier=resolved_group,
        sequence_index=sequence_index,
        timestamp=timestamp_ms,
        location=location,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=asset,
        amount=FVal(amount),
        location_label=location_label,
        notes=notes,
        extra_data=extra_data,
    )


class _EmptyEVMAccountingAggregator(EVMAccountingAggregator):
    def initialize_all_accountants(self) -> None:
        self.accountants = {}


class _RealProtocolEVMAccountingAggregator(EVMAccountingAggregator):
    """Wires real Aave v2, MakerDAO, and The Graph accountants with stubbed node_inquirer."""

    def initialize_all_accountants(self) -> None:
        self.accountants = {
            'aavev2': Aavev2Accountant(
                node_inquirer=self.node_inquirer,
                msg_aggregator=self.msg_aggregator,
            ),
            'makerdao': MakerdaoAccountant(
                node_inquirer=self.node_inquirer,
                msg_aggregator=self.msg_aggregator,
            ),
            'thegraph': ThegraphAccountant(
                node_inquirer=self.node_inquirer,
                msg_aggregator=self.msg_aggregator,
            ),
        }


def _make_chains_aggregator(
        database: DBHandler,
        use_real_evm_accountants: bool,
) -> MagicMock:
    node_inquirer_stub = MagicMock()
    empty_aggregator = _EmptyEVMAccountingAggregator(
        node_inquirer=node_inquirer_stub,
        msg_aggregator=database.msg_aggregator,
        modules_path='',
    )
    eth_aggregator: EVMAccountingAggregator = (
        _RealProtocolEVMAccountingAggregator(
            node_inquirer=node_inquirer_stub,
            msg_aggregator=database.msg_aggregator,
            modules_path='',
        )
        if use_real_evm_accountants
        else empty_aggregator
    )

    def _get_evm_manager(chain_id: ChainID) -> MagicMock:
        manager = MagicMock()
        manager.accounting_aggregator = (
            eth_aggregator if chain_id == ChainID.ETHEREUM else empty_aggregator
        )
        return manager

    chains_aggregator = MagicMock()
    chains_aggregator.get_evm_manager.side_effect = _get_evm_manager
    return chains_aggregator


def _load_default_accounting_rules(database: DBHandler) -> None:
    global _DEFAULT_RULES_CACHE  # noqa: PLW0603
    if _DEFAULT_RULES_CACHE is None:
        parsed: list[tuple[int, list[dict[str, Any]]]] = []
        for version in range(1, LAST_ACCOUNTING_RULES_VERSION + 1):
            rules_file = _ensure_accounting_rules(version)
            parsed.append((version, _read_rules_from_file(rules_file)))
        _DEFAULT_RULES_CACHE = parsed

    data_updater = RotkiDataUpdater(
        msg_aggregator=database.msg_aggregator,
        user_db=database,
    )
    for version, rules in _DEFAULT_RULES_CACHE:
        data_updater.update_accounting_rules(data=rules, version=version)


def _make_price_fn(scenario: ParityScenario) -> Callable[[Asset, Asset, Timestamp], Price]:
    def price_fn(from_asset: Asset, to_asset: Asset, timestamp: Timestamp) -> Price:
        if (from_asset, to_asset, timestamp) in scenario.pair_prices:
            return scenario.pair_prices[from_asset, to_asset, timestamp]
        if (from_asset, timestamp) in scenario.prices:
            return scenario.prices[from_asset, timestamp]
        if from_asset == to_asset:
            return Price(ONE)
        if from_asset in scenario.default_prices:
            return scenario.default_prices[from_asset]
        raise NoPriceForGivenTimestamp(from_asset=from_asset, to_asset=to_asset, time=timestamp)

    return price_fn


def _pnl_filter(start_ts: Timestamp, end_ts: Timestamp) -> HistoryEventFilterQuery:
    return HistoryEventFilterQuery.make(
        from_ts=start_ts,
        to_ts=end_ts,
        exclude_ignored_assets=True,
        exclude_ignored_actions=True,
        exclude_untracked_withdrawals=True,
    )


def _legacy_event_sort_key(event: AccountingEventMixin) -> tuple[int, str, int]:
    if isinstance(event, HistoryBaseEntry):
        return (int(event.timestamp), event.group_identifier, event.sequence_index)
    return (int(ts_sec_to_ms(event.get_timestamp())), '', 0)


def _load_cost_basis_rows(database: DBHandler) -> list[dict[str, Any]]:
    with database.conn.read_ctx() as cursor:
        return [
            {
                'event_identifier': row[0],
                'group_identifier': row[1],
                'event_type': row[2],
                'event_subtype': row[3],
                'timestamp': row[4],
                'sequence_index': row[5],
                'location': row[6],
                'location_label': row[7],
                'protocol': row[8],
                'asset': row[9],
                'direction': row[10],
                'lot_created_id': row[11],
                'basis_per_unit': row[12],
                'basis_source': row[13],
                'lots_consumed_json': row[14],
                'proceeds': row[15],
                'realized_pnl': row[16],
                'taxfree_pnl': row[17],
                'basis_removed': row[18],
                'post_spend_basis_remaining': row[19],
                'is_taxable': bool(row[20]),
                'method': row[21],
            }
            for row in cursor.execute(
                'SELECT cb.event_identifier, he.group_identifier, he.type, he.subtype, '
                'cb.timestamp, cb.sequence_index, cb.location, cb.location_label, cb.protocol, '
                'cb.asset, cb.direction, cb.lot_created_id, cb.basis_per_unit, cb.basis_source, '
                'cb.lots_consumed_json, cb.proceeds, cb.realized_pnl, cb.taxfree_pnl, '
                'cb.basis_removed, cb.post_spend_basis_remaining, cb.is_taxable, cb.method '
                'FROM event_cost_basis AS cb '
                'JOIN history_events AS he ON cb.event_identifier = he.identifier '
                'ORDER BY cb.timestamp, cb.sequence_index, cb.id',
            )
        ]


def _build_per_asset_diff(
        old_events: Sequence[ProcessedAccountingEvent],
        new_breakdown: Sequence[Mapping[str, Any]],
) -> dict[str, AssetPnlDiff]:
    old_by_asset: dict[str, tuple[FVal, FVal]] = {}
    for event in old_events:
        asset_id = event.asset.identifier
        prev_taxable, prev_free = old_by_asset.get(asset_id, (ZERO, ZERO))
        old_by_asset[asset_id] = (
            prev_taxable + event.pnl.taxable,
            prev_free + event.pnl.free,
        )

    new_by_asset: dict[str, tuple[FVal, FVal]] = {}
    for row in new_breakdown:
        group_key = row['group_key']
        asset_id = '' if group_key is None else str(group_key)
        prev_taxable, prev_free = new_by_asset.get(asset_id, (ZERO, ZERO))
        new_by_asset[asset_id] = (
            prev_taxable + FVal(row['realized_pnl']),
            prev_free + FVal(row['taxfree_pnl']),
        )

    per_asset: dict[str, AssetPnlDiff] = {}
    for asset_id in sorted(set(old_by_asset) | set(new_by_asset)):
        old_taxable, old_free = old_by_asset.get(asset_id, (ZERO, ZERO))
        new_taxable, new_free = new_by_asset.get(asset_id, (ZERO, ZERO))
        per_asset[asset_id] = AssetPnlDiff(
            asset=asset_id,
            old_taxable=old_taxable,
            old_free=old_free,
            new_taxable=new_taxable,
            new_free=new_free,
        )
    return per_asset


def run_parity_scenario(database: DBHandler, scenario: ParityScenario) -> ParityDiff:
    """Persist `scenario` into `database`, run both pipelines, and return a 3-level `ParityDiff`."""  # noqa: E501
    settings_dict = dict(scenario.settings)
    raw_main_currency = settings_dict.pop('main_currency', A_USD)
    main_currency = raw_main_currency.resolve_to_asset_with_oracles()

    with database.user_write() as write_cursor:
        database.set_settings(
            write_cursor,
            ModifiableDBSettings(
                main_currency=main_currency,
                cost_basis_method=scenario.method,
                **settings_dict,
            ),
        )
        if scenario.blockchain_accounts:
            database.add_blockchain_accounts(
                write_cursor=write_cursor,
                account_data=list(scenario.blockchain_accounts),
            )
        for asset in scenario.ignored_assets:
            database.add_to_ignored_assets(write_cursor=write_cursor, asset=asset)
        if scenario.ignored_actions:
            ignored_ids = [
                item if isinstance(item, str) else item.group_identifier
                for item in scenario.ignored_actions
            ]
            database.add_to_ignored_action_ids(
                write_cursor=write_cursor,
                identifiers=ignored_ids,
            )
        if scenario.events:
            DBHistoryEvents(database).add_history_events(
                write_cursor=write_cursor,
                history=list(scenario.events),
            )

    if scenario.use_default_rules:
        _load_default_accounting_rules(database)

    if scenario.rules:
        db_rules = DBAccountingRules(database)
        for rule_spec in scenario.rules:
            db_rules.add_accounting_rule(
                event_type=rule_spec.event_type,
                event_subtype=rule_spec.event_subtype,
                counterparty=rule_spec.counterparty,
                rule=BaseEventSettings(
                    taxable=rule_spec.taxable,
                    count_entire_amount_spend=rule_spec.count_entire_amount_spend,
                    count_cost_basis_pnl=rule_spec.count_cost_basis_pnl,
                    accounting_treatment=rule_spec.accounting_treatment,
                ),
                links=dict(rule_spec.links),
                force_update=rule_spec.force_update,
                event_ids=list(rule_spec.event_ids) if rule_spec.event_ids is not None else None,
            )

    if scenario.run_balance_pass:
        assert process_historical_balances(database, database.msg_aggregator) is True

    price_fn = _make_price_fn(scenario)
    with (
        patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as new_historian,
        patch('rotkehlchen.accounting.pot.PriceHistorian') as old_historian,
        patch('rotkehlchen.history.price.PriceHistorian') as global_historian,
    ):
        new_historian.return_value.query_historical_price = price_fn
        old_historian.return_value.query_historical_price = price_fn
        global_historian.return_value.query_historical_price = price_fn

        assert process_cost_basis(database, database.msg_aggregator) is True
        new_result = query_realized_pnl(
            database=database,
            filter_query=_pnl_filter(scenario.start_ts, scenario.end_ts),
            group_by=RealizedPnlGroupBy.ASSET,
        )
        new_cost_basis_rows = _load_cost_basis_rows(database)

        with database.conn.read_ctx() as cursor:
            db_events = DBHistoryEvents(database).get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    from_ts=Timestamp(0),
                    to_ts=scenario.end_ts,
                    exclude_untracked_withdrawals=True,
                ),
                aggregate_by_group_ids=False,
            )

        legacy_events: list[AccountingEventMixin] = [
            *db_events,
            *scenario.extra_legacy_events,
        ]
        legacy_events.sort(key=_legacy_event_sort_key)

        premium = MagicMock()
        premium.is_active.return_value = True
        accountant = Accountant(
            db=database,
            msg_aggregator=database.msg_aggregator,
            chains_aggregator=_make_chains_aggregator(
                database=database,
                use_real_evm_accountants=scenario.use_real_evm_accountants,
            ),
            premium=premium,
        )
        accountant.process_history(
            start_ts=scenario.start_ts,
            end_ts=scenario.end_ts,
            events=legacy_events,
        )

    pot = accountant.pots[0]
    old_events = list(pot.processed_events)
    per_asset = _build_per_asset_diff(
        old_events=old_events,
        new_breakdown=new_result['breakdown'],
    )
    return ParityDiff(
        scenario_id=scenario.id,
        old_taxable=pot.pnls.taxable,
        old_free=pot.pnls.free,
        new_taxable=FVal(new_result['total_realized_pnl']),
        new_free=FVal(new_result['total_taxfree_pnl']),
        stale=bool(new_result['stale']),
        old_missing_prices=set(pot.cost_basis.missing_prices),
        new_unpriced_events=int(new_result['num_unpriced_events']),
        per_asset=per_asset,
        old_events=old_events,
        new_cost_basis_rows=new_cost_basis_rows,
        new_result=new_result,
    )
