import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UNMATCHED_ACTIONS, type UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import { type UnmatchedBridgeRow, useUnmatchedBridgeRows } from '@/modules/history/events/use-unmatched-bridge-rows';

const { spies } = vi.hoisted(() => ({
  spies: {
    isCounterpartUntracked: vi.fn<() => boolean>(() => false),
  },
}));

vi.mock('@/modules/history/events/use-untracked-bridge-counterpart', () => ({
  canCreateBridgeCounterpart: (): boolean => false,
  getBridgeCounterpartAddress: (): string | undefined => undefined,
  isCounterpartUnqueryable: (): boolean => false,
  useUntrackedBridgeCounterpart: (): object => ({
    isCounterpartUntracked: spies.isCounterpartUntracked,
  }),
}));

function createMockTransaction(direction: 'deposit' | 'withdrawal'): UnmatchedBridgeTransaction {
  return {
    asset: 'ETH',
    direction,
    // @ts-expect-error partial mock: the row only reads the leg's entry
    events: { entry: { identifier: 1, location: 'ethereum', timestamp: 1700000000000 } },
    groupIdentifier: 'group1',
    identifier: 1,
  };
}

function rowFor(direction: 'deposit' | 'withdrawal'): { row: UnmatchedBridgeRow; spec: UnmatchedRowActionSpec } {
  const { rows, specFor } = useUnmatchedBridgeRows({
    matchDisabled: false,
    showRestore: false,
    transactions: [createMockTransaction(direction)],
  });
  const row = get(rows)[0];
  return { row, spec: specFor(row) };
}

describe('use-unmatched-bridge-rows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spies.isCounterpartUntracked.mockReturnValue(false);
  });

  describe('mark external', () => {
    it('should ask about a payment out when confirming a deposit', () => {
      const { spec } = rowFor('deposit');

      expect(spec.confirms?.[UNMATCHED_ACTIONS.MARK_EXTERNAL]?.message).toBe(
        'bridge_matching.dialog.confirm_mark_external',
      );
    });

    it('should ask about income in when confirming a withdrawal', () => {
      const { spec } = rowFor('withdrawal');

      expect(spec.confirms?.[UNMATCHED_ACTIONS.MARK_EXTERNAL]?.message).toBe(
        'bridge_matching.dialog.confirm_mark_external_in',
      );
    });

    it('should describe the action itself by direction too', () => {
      expect(rowFor('deposit').spec.markExternal?.tooltip).toBe('bridge_matching.dialog.mark_external_tooltip');
      expect(rowFor('withdrawal').spec.markExternal?.tooltip).toBe('bridge_matching.dialog.mark_external_in_tooltip');
    });

    it('should skip the confirm when the counterpart is known to be untracked', () => {
      spies.isCounterpartUntracked.mockReturnValue(true);

      const { spec } = rowFor('withdrawal');

      expect(spec.confirms?.[UNMATCHED_ACTIONS.MARK_EXTERNAL]).toBeUndefined();
      // ...but the row still asks before ignoring, so the skip is specific, not a missing map
      expect(spec.confirms?.[UNMATCHED_ACTIONS.IGNORE]).toBeDefined();
    });
  });

  it('should label the row by direction', () => {
    expect(rowFor('deposit').row.directionLabel).toBe('bridge_matching.dialog.direction_out');
    expect(rowFor('withdrawal').row.directionLabel).toBe('bridge_matching.dialog.direction_in');
  });
});
