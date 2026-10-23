import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import { createAssetMovementEvent, createOnlineHistoryEvent } from '@test/utils/history-events';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UNMATCHED_ACTIONS, type UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import { type UnmatchedMovementRow, useUnmatchedMovementRows } from '@/modules/history/events/use-unmatched-movement-rows';

const { spies } = vi.hoisted(() => ({
  spies: {
    isDestinationUntracked: vi.fn<() => boolean>(() => false),
  },
}));

vi.mock('@/modules/history/events/use-untracked-movement-destination', () => ({
  getMovementDestinationAddress: (): string | undefined => undefined,
  useUntrackedMovementDestination: (): object => ({
    isDestinationUntracked: spies.isDestinationUntracked,
  }),
}));

/** Wraps one event as the single-entry group the panel receives. */
function movementFor(entry: HistoryEventEntry): UnmatchedAssetMovement {
  return {
    asset: 'ETH',
    events: { entry, eventAccountingRuleStatus: entry.eventAccountingRuleStatus },
    groupIdentifier: 'group1',
    isFiat: false,
  };
}

/** Creates an unresolved movement, whose direction still lives in its subtype. */
function createMockMovement(eventSubtype: 'spend' | 'receive'): UnmatchedAssetMovement {
  return movementFor(createAssetMovementEvent({ eventSubtype, eventType: 'exchange transfer', location: 'kraken' }));
}

/** Creates a movement carrying the stamp the backend writes when it resolves one as external. */
function createResolvedMovement(direction: 'deposit' | 'withdrawal'): UnmatchedAssetMovement {
  return movementFor(createOnlineHistoryEvent({
    eventSubtype: 'payment',
    eventType: direction === 'deposit' ? 'receive' : 'spend',
    extraData: { matchedAssetMovement: { direction, resolution: 'external' } },
    location: 'kraken',
  }));
}

/** Creates a plain history event in the ignored tab that the backend never resolved. */
function createUnstampedMovement(): UnmatchedAssetMovement {
  return movementFor(createOnlineHistoryEvent({ eventSubtype: 'payment', eventType: 'receive', location: 'kraken' }));
}

/**
 * Builds the row and its action spec, which is what every assertion here reads.
 *
 * @param movement - the single movement the model is given
 * @param showRestore - render it as an ignored row rather than an unmatched one
 */
function rowForMovement(
  movement: UnmatchedAssetMovement,
  showRestore = false,
): { row: UnmatchedMovementRow; spec: UnmatchedRowActionSpec } {
  const { rows, specFor } = useUnmatchedMovementRows({
    matchDisabled: false,
    movements: [movement],
    showRestore,
  });
  const row = get(rows)[0];
  return { row, spec: specFor(row) };
}

/** Narrows {@link rowForMovement} to the common case of an unresolved movement. */
function rowFor(
  eventSubtype: 'spend' | 'receive',
  showRestore = false,
): { row: UnmatchedMovementRow; spec: UnmatchedRowActionSpec } {
  return rowForMovement(createMockMovement(eventSubtype), showRestore);
}

describe('use-unmatched-movement-rows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spies.isDestinationUntracked.mockReturnValue(false);
  });

  describe('mark external', () => {
    it('should ask about a payment out when confirming a withdrawal', () => {
      expect(rowFor('spend').spec.confirms?.[UNMATCHED_ACTIONS.MARK_EXTERNAL]?.message).toBe(
        'asset_movement_matching.dialog.confirm_mark_external',
      );
    });

    it('should ask about income in when confirming a deposit', () => {
      expect(rowFor('receive').spec.confirms?.[UNMATCHED_ACTIONS.MARK_EXTERNAL]?.message).toBe(
        'asset_movement_matching.dialog.confirm_mark_external_in',
      );
    });

    it('should describe the action itself by direction too', () => {
      expect(rowFor('spend').spec.markExternal?.tooltip).toBe('asset_movement_matching.dialog.mark_external_tooltip');
      expect(rowFor('receive').spec.markExternal?.tooltip).toBe('asset_movement_matching.dialog.mark_external_in_tooltip');
    });

    it('should offer the action on every row, so an unmatchable movement is never stuck', () => {
      expect(rowFor('spend').spec.markExternal).toBeDefined();
      expect(rowFor('receive').spec.markExternal).toBeDefined();
    });

    it('should skip the confirm and emphasize when the destination is known to be untracked', () => {
      spies.isDestinationUntracked.mockReturnValue(true);

      const { row, spec } = rowFor('spend');

      expect(row.untrackedDestination).toBe(true);
      expect(spec.markExternal?.emphasize).toBe(true);
      expect(spec.confirms?.[UNMATCHED_ACTIONS.MARK_EXTERNAL]).toBeUndefined();
    });

    it('should still ask before ignoring an untracked row, so the skip is specific', () => {
      spies.isDestinationUntracked.mockReturnValue(true);

      expect(rowFor('spend').spec.confirms?.[UNMATCHED_ACTIONS.IGNORE]).toBeDefined();
    });
  });

  describe('the empty text', () => {
    it('should say there is nothing to match while nothing failed', () => {
      const { emptyDescription } = useUnmatchedMovementRows({ matchDisabled: false, movements: [], showRestore: false });

      expect(get(emptyDescription)).toBe('asset_movement_matching.dialog.no_unmatched');
    });

    it('should keep the empty text when a load failed, leaving the failure to the list', () => {
      const { emptyDescription } = useUnmatchedMovementRows({ error: new Error('backend down'), matchDisabled: false, movements: [], showRestore: false });

      expect(get(emptyDescription)).toBe('asset_movement_matching.dialog.no_unmatched');
    });
  });

  describe('the failure', () => {
    it('should name the unmatched list and the reason it got back', () => {
      const { failure } = useUnmatchedMovementRows({ error: new Error('backend down'), matchDisabled: false, movements: [], showRestore: false });

      expect(get(failure)).toEqual({ message: 'backend down', title: 'asset_movement_matching.dialog.load_failed.unmatched' });
    });

    it('should name the ignored list on the ignored tab', () => {
      const { failure } = useUnmatchedMovementRows({ error: new Error('backend down'), matchDisabled: false, movements: [], showRestore: true });

      expect(get(failure)?.title).toBe('asset_movement_matching.dialog.load_failed.ignored');
    });

    it('should name no failure while nothing failed', () => {
      const { failure } = useUnmatchedMovementRows({ matchDisabled: false, movements: [], showRestore: false });

      expect(get(failure)).toBeUndefined();
    });
  });

  it('should label the row by direction', () => {
    expect(rowFor('spend').row.direction).toBe('withdrawal');
    expect(rowFor('receive').row.direction).toBe('deposit');
  });

  it('should not claim an untracked destination on an already ignored row', () => {
    spies.isDestinationUntracked.mockReturnValue(true);

    expect(rowFor('spend', true).row.untrackedDestination).toBe(false);
  });

  describe('an already resolved row', () => {
    it('should take its direction from the stamp of a resolved deposit', () => {
      const { row } = rowForMovement(createResolvedMovement('deposit'), true);

      expect(row.direction).toBe('deposit');
      expect(row.resolvedAsExternal).toBe(true);
      expect(row.resolvedLabel).toBe('asset_movement_matching.dialog.resolved_income');
    });

    it('should take its direction from the stamp of a resolved withdrawal', () => {
      const { row } = rowForMovement(createResolvedMovement('withdrawal'), true);

      expect(row.direction).toBe('withdrawal');
      expect(row.resolvedLabel).toBe('asset_movement_matching.dialog.resolved_payment');
    });

    it('should not mark a merely ignored movement as resolved', () => {
      expect(rowFor('receive', true).row.resolvedAsExternal).toBe(false);
    });

    it('should not mark an unstamped history event as resolved', () => {
      expect(rowForMovement(createUnstampedMovement(), true).row.resolvedAsExternal).toBe(false);
    });
  });
});
