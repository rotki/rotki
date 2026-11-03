import type { assetMovementMatchingKind } from '@/modules/history/events/matching/asset-movement-matching-kind';
import type { bridgeMatchingKind } from '@/modules/history/events/matching/bridge-matching-kind';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import type { UnmatchedBridgeRow } from '@/modules/history/events/use-unmatched-bridge-rows';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import type { UnmatchedMovementRow } from '@/modules/history/events/use-unmatched-movement-rows';
import { createAssetMovementEvent, createEvmEvent } from '@test/utils/history-events';
import { defineComponent } from 'vue';
import { UnmatchedVariant } from '@/modules/history/events/unmatched-row';

/** Either real matching kind, each with its own item type; the shared panels accept both. */
export type AnyMatchingKind = typeof assetMovementMatchingKind | typeof bridgeMatchingKind;

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
  variant: UnmatchedVariant;
  /** The group a row belongs to, which a deep link highlights. */
  groupOf: (key: string) => string;
  locationLabel: string;
  row: (rowCase: UnmatchedRowCase) => UnmatchedBridgeRow | UnmatchedMovementRow;
}

export const plainRow: UnmatchedRowCase = { key: 'row-1', typeLabel: 'Deposit' };

export const untrackedRow: UnmatchedRowCase = {
  key: 'row-2',
  typeLabel: 'Withdrawal',
  untracked: { label: 'Untracked destination', tooltip: 'Not one of your accounts' },
};

/** Stands in for the row actions: one button that reports an ignore, without selecting the row it sits on. */
export const UnmatchedActionsStub = defineComponent({
  name: 'UnmatchedActions',
  props: ['spec'],
  emits: ['action'],
  template: '<button data-testid="row-action" @click.stop="$emit(\'action\', \'ignore\')" />',
});

const TIMESTAMP = 1700000000000;

function bridgeGroupOf(key: string): string {
  return `${key}-group`;
}

function bridgeRow({ key, typeLabel, untracked }: UnmatchedRowCase): UnmatchedBridgeRow {
  const groupIdentifier = bridgeGroupOf(key);
  const original: UnmatchedBridgeTransaction = {
    asset: 'ETH',
    direction: 'deposit',
    events: [],
    groupIdentifier,
    identifier: 1,
  };
  return {
    canCreateCounterpart: false,
    direction: 'deposit',
    entry: createEvmEvent({ groupIdentifier, location: 'ethereum', timestamp: TIMESTAMP }),
    groupIdentifier,
    id: key,
    location: 'ethereum',
    original,
    timestamp: TIMESTAMP,
    typeLabel,
    unqueryableCounterpart: false,
    untracked: !!untracked,
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
  extras: Partial<Pick<UnmatchedMovementRow, 'isFiat' | 'resolvedLabel' | 'untrackedAddress'>> = {},
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
    groupIdentifier: key,
    id: key,
    isFiat: false,
    location: 'kraken',
    original,
    timestamp: TIMESTAMP,
    typeLabel,
    untracked: !!untracked,
    untrackedLabel: untracked?.label ?? '',
    untrackedTooltip: untracked?.tooltip ?? '',
    ...extras,
  };
}

const BRIDGE_KIND: UnmatchedPanelKind = {
  groupOf: bridgeGroupOf,
  locationLabel: 'common.location',
  name: 'bridge',
  row: bridgeRow,
  variant: UnmatchedVariant.BRIDGE,
};

export const MOVEMENT_KIND: UnmatchedPanelKind = {
  groupOf: key => key,
  locationLabel: 'common.exchange',
  name: 'asset movement',
  row: rowCase => movementRow(rowCase),
  variant: UnmatchedVariant.ASSET_MOVEMENT,
};

export const UNMATCHED_PANEL_KINDS: UnmatchedPanelKind[] = [BRIDGE_KIND, MOVEMENT_KIND];
