import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import type { UnmatchedBridgeRow } from '@/modules/history/events/use-unmatched-bridge-rows';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import type { UnmatchedMovementRow } from '@/modules/history/events/use-unmatched-movement-rows';
import { createAssetMovementEvent } from '@test/utils/history-events';

/** What a test says about a row, in words both kinds understand. */
export interface UnmatchedRowCase {
  /** What the selection model stores for the row. */
  key: string;
  typeLabel: string;
  untracked?: { label: string; tooltip: string };
}

/** The kind-specific parts of an unmatched panel that a spec over both kinds has to know. */
export interface UnmatchedPanelKind {
  name: 'bridge' | 'asset movement';
  /** The group a row belongs to, which a deep link highlights. */
  groupOf: (key: string) => string;
  locationLabel: string;
  actionsLabel: string;
  untrackedReasonKey: string;
  row: (rowCase: UnmatchedRowCase) => UnmatchedBridgeRow | UnmatchedMovementRow;
}

const TIMESTAMP = 1700000000000;

function bridgeRow({ key, typeLabel, untracked }: UnmatchedRowCase): UnmatchedBridgeRow {
  const original: UnmatchedBridgeTransaction = {
    asset: 'ETH',
    direction: 'deposit',
    events: [],
    groupIdentifier: `${key}-group`,
    identifier: 1,
  };
  return {
    canCreateCounterpart: false,
    direction: 'deposit',
    directionLabel: typeLabel,
    entry: createAssetMovementEvent({ groupIdentifier: `${key}-group`, location: 'ethereum', timestamp: TIMESTAMP }),
    groupIdentifier: `${key}-group`,
    id: key,
    location: 'ethereum',
    original,
    timestamp: TIMESTAMP,
    unqueryableCounterpart: false,
    untrackedCounterpart: !!untracked,
    untrackedLabel: untracked?.label ?? '',
    untrackedTooltip: untracked?.tooltip ?? '',
  };
}

/**
 * A movement row.
 *
 * @remarks
 * A movement is matched as a whole group, so its key is its group identifier.
 */
export function movementRow(
  { key, typeLabel, untracked }: UnmatchedRowCase,
  extras: Partial<Pick<UnmatchedMovementRow, 'destinationAddress' | 'isFiat' | 'resolvedAsExternal' | 'resolvedLabel'>> = {},
): UnmatchedMovementRow {
  const original: UnmatchedAssetMovement = {
    asset: 'ETH',
    events: [],
    groupIdentifier: key,
    isFiat: extras.isFiat ?? false,
  };
  return {
    direction: 'withdrawal',
    entry: createAssetMovementEvent({ groupIdentifier: key, location: 'kraken', timestamp: TIMESTAMP }),
    eventSubtype: 'remove asset',
    groupIdentifier: key,
    isFiat: false,
    location: 'kraken',
    original,
    resolvedAsExternal: false,
    resolvedLabel: '',
    timestamp: TIMESTAMP,
    typeLabel,
    untrackedDestination: !!untracked,
    untrackedLabel: untracked?.label ?? '',
    untrackedTooltip: untracked?.tooltip ?? '',
    ...extras,
  };
}

export const UNMATCHED_PANEL_KINDS: UnmatchedPanelKind[] = [
  {
    actionsLabel: 'bridge_matching.dialog.manual_action',
    groupOf: key => `${key}-group`,
    locationLabel: 'common.location',
    name: 'bridge',
    row: bridgeRow,
    untrackedReasonKey: 'bridge_matching.dialog.untracked_reason',
  },
  {
    actionsLabel: 'asset_movement_matching.dialog.manual_action',
    groupOf: key => key,
    locationLabel: 'common.exchange',
    name: 'asset movement',
    row: rowCase => movementRow(rowCase),
    untrackedReasonKey: 'asset_movement_matching.dialog.untracked_reason',
  },
];
