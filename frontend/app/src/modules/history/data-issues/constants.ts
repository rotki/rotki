import type { RuiIcons } from '@rotki/ui-library';

/**
 * Kinds of data issues the accounting engine can detect. Mirrors the backend
 * `IssueKind` StrEnum (rotkehlchen/history/data_issues/constants.py).
 */
export enum IssueKind {
  CURRENT_BALANCE_MISMATCH = 'current_balance_mismatch',
  INCOMPLETE_SWAP = 'incomplete_swap',
  INVALID_EVENT_AMOUNT = 'invalid_event_amount',
  MISSING_COST_BASIS = 'missing_cost_basis',
  MISSING_PRICE = 'missing_price',
  NEGATIVE_BALANCE = 'negative_balance',
  REBASING_TOKEN = 'rebasing_token',
  UNMATCHED_BRIDGE = 'unmatched_bridge',
  UNMATCHED_EXCHANGE_TRANSFER = 'unmatched_exchange_transfer',
}

/**
 * Lifecycle states of a data issue. Mirrors the backend `IssueState` StrEnum.
 * `open`, `auto_remediating` and `unresolved` are the non-terminal states the
 * inbox shows by default; `resolved` and `dismissed` are terminal.
 */
export enum IssueState {
  OPEN = 'open',
  AUTO_REMEDIATING = 'auto_remediating',
  UNRESOLVED = 'unresolved',
  RESOLVED = 'resolved',
  DISMISSED = 'dismissed',
}

/** Severity of a data issue. Only `warning` exists for now. */
export enum IssueSeverity {
  WARNING = 'warning',
}

/** Non-terminal states, used for the pinned/overlay panel preview. */
export const NON_TERMINAL_STATES: readonly IssueState[] = [
  IssueState.OPEN,
  IssueState.AUTO_REMEDIATING,
  IssueState.UNRESOLVED,
] as const;

/**
 * Default state filter for the main inbox list (issue #12294): the issues the
 * user still needs to act on, i.e. open plus auto-remediation that gave up.
 * Auto-remediating rows are transient and excluded from the default view.
 */
export const DEFAULT_LIST_STATES: readonly IssueState[] = [
  IssueState.OPEN,
  IssueState.UNRESOLVED,
] as const;

type ChipColor = 'grey' | 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success';

interface StateMeta {
  readonly color: ChipColor;
  readonly icon: RuiIcons;
  /** Whether the state shows an in-progress spinner (auto-remediation running). */
  readonly busy?: boolean;
}

export const STATE_META: Record<IssueState, StateMeta> = {
  [IssueState.OPEN]: { color: 'warning', icon: 'lu-circle-dot' },
  [IssueState.AUTO_REMEDIATING]: { busy: true, color: 'info', icon: 'lu-loader-circle' },
  [IssueState.UNRESOLVED]: { color: 'error', icon: 'lu-circle-alert' },
  [IssueState.RESOLVED]: { color: 'success', icon: 'lu-circle-check' },
  [IssueState.DISMISSED]: { color: 'grey', icon: 'lu-circle-slash' },
};

interface KindMeta {
  readonly color: ChipColor;
  readonly icon: RuiIcons;
}

export const KIND_META: Record<IssueKind, KindMeta> = {
  [IssueKind.NEGATIVE_BALANCE]: { color: 'error', icon: 'lu-trending-down' },
  [IssueKind.INVALID_EVENT_AMOUNT]: { color: 'error', icon: 'lu-circle-alert' },
  [IssueKind.CURRENT_BALANCE_MISMATCH]: { color: 'warning', icon: 'lu-scale' },
  [IssueKind.REBASING_TOKEN]: { color: 'warning', icon: 'lu-refresh-cw' },
  [IssueKind.UNMATCHED_BRIDGE]: { color: 'warning', icon: 'lu-git-compare-arrows' },
  [IssueKind.MISSING_PRICE]: { color: 'warning', icon: 'lu-circle-dollar-sign' },
  [IssueKind.MISSING_COST_BASIS]: { color: 'error', icon: 'lu-receipt' },
  [IssueKind.INCOMPLETE_SWAP]: { color: 'warning', icon: 'lu-repeat' },
  [IssueKind.UNMATCHED_EXCHANGE_TRANSFER]: { color: 'warning', icon: 'lu-arrow-left-right' },
};

/**
 * Whether each action is allowed from a given state, mirroring the backend
 * transition rules (rotkehlchen/history/data_issues/manager.py):
 *  - dismiss: any non-terminal state (terminal states are already closed).
 *  - resolveManually: blocked once resolved or dismissed.
 *  - reopen: allowed for terminal states (`resolved` or `dismissed`).
 *  - retry: available for rebasing and unmatched-exchange-transfer issues that are open or unresolved.
 */
export function canDismiss(state: IssueState): boolean {
  return state !== IssueState.RESOLVED && state !== IssueState.DISMISSED;
}

export function canResolveManually(state: IssueState): boolean {
  return state !== IssueState.RESOLVED && state !== IssueState.DISMISSED;
}

export function canReopen(state: IssueState): boolean {
  return state === IssueState.RESOLVED || state === IssueState.DISMISSED;
}

export function canRetry(kind: IssueKind, state: IssueState): boolean {
  return (kind === IssueKind.REBASING_TOKEN || kind === IssueKind.UNMATCHED_EXCHANGE_TRANSFER)
    && (state === IssueState.OPEN || state === IssueState.UNRESOLVED);
}
