import type { RuiIcons } from '@rotki/ui-library';

/**
 * Kinds of data issues the accounting engine can detect. Mirrors the backend
 * `IssueKind` StrEnum (rotkehlchen/history/data_issues/constants.py).
 */
export enum IssueKind {
  CURRENT_BALANCE_MISMATCH = 'current_balance_mismatch',
  NEGATIVE_BALANCE = 'negative_balance',
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

/** Non-terminal states — these are the inbox's default filter selection. */
export const NON_TERMINAL_STATES: readonly IssueState[] = [
  IssueState.OPEN,
  IssueState.AUTO_REMEDIATING,
  IssueState.UNRESOLVED,
] as const;

export type ChipColor = 'grey' | 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success';

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
  [IssueKind.CURRENT_BALANCE_MISMATCH]: { color: 'warning', icon: 'lu-scale' },
};

/**
 * Whether each action is allowed from a given state, mirroring the backend
 * transition rules (rotkehlchen/history/data_issues/manager.py):
 *  - dismiss: any non-terminal state (terminal states are already closed).
 *  - resolveManually: blocked once resolved or dismissed.
 *  - retry: blocked once dismissed; a no-op (still allowed) for open/auto_remediating.
 */
export function canDismiss(state: IssueState): boolean {
  return state !== IssueState.RESOLVED && state !== IssueState.DISMISSED;
}

export function canResolveManually(state: IssueState): boolean {
  return state !== IssueState.RESOLVED && state !== IssueState.DISMISSED;
}

export function canRetry(state: IssueState): boolean {
  return state !== IssueState.DISMISSED && state !== IssueState.RESOLVED;
}
