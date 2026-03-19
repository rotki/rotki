import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type InternalTxConflict, InternalTxConflictActions } from './types';
import { useInternalTxConflictSelection } from './use-internal-tx-conflict-selection';

function createMockConflict(overrides: Partial<InternalTxConflict> = {}): InternalTxConflict {
  return {
    action: InternalTxConflictActions.REPULL,
    chain: 'ethereum',
    groupIdentifier: null,
    lastError: null,
    lastRetryTs: null,
    redecodeReason: null,
    repullReason: 'all_zero_gas',
    timestamp: null,
    txHash: '0xabc',
    ...overrides,
  };
}

describe('use-internal-tx-conflict-selection', () => {
  let composable: ReturnType<typeof useInternalTxConflictSelection>;

  beforeEach(() => {
    composable = useInternalTxConflictSelection();
    composable.clearSelection();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('toggleSelection', () => {
    it('adds a conflict to selection', () => {
      const conflict = createMockConflict();
      composable.toggleSelection(conflict);

      expect(composable.isSelected(conflict)).toBe(true);
      expect(get(composable.selectedCount)).toBe(1);
    });

    it('removes a conflict from selection when toggled again', () => {
      const conflict = createMockConflict();
      composable.toggleSelection(conflict);
      composable.toggleSelection(conflict);

      expect(composable.isSelected(conflict)).toBe(false);
      expect(get(composable.selectedCount)).toBe(0);
    });

    it('handles multiple conflicts from different chains', () => {
      const conflict1 = createMockConflict({ chain: 'ethereum', txHash: '0x111' });
      const conflict2 = createMockConflict({ chain: 'optimism', txHash: '0x111' });

      composable.toggleSelection(conflict1);
      composable.toggleSelection(conflict2);

      expect(composable.isSelected(conflict1)).toBe(true);
      expect(composable.isSelected(conflict2)).toBe(true);
      expect(get(composable.selectedCount)).toBe(2);
    });
  });

  describe('isSelected', () => {
    it('returns false for unselected conflict', () => {
      const conflict = createMockConflict();
      expect(composable.isSelected(conflict)).toBe(false);
    });
  });

  describe('clearSelection', () => {
    it('removes all selections', () => {
      const c1 = createMockConflict({ txHash: '0x111' });
      const c2 = createMockConflict({ txHash: '0x222' });

      composable.toggleSelection(c1);
      composable.toggleSelection(c2);
      expect(get(composable.selectedCount)).toBe(2);

      composable.clearSelection();
      expect(get(composable.selectedCount)).toBe(0);
      expect(get(composable.selectedConflicts)).toHaveLength(0);
    });
  });

  describe('toggleAllOnPage', () => {
    it('selects all page conflicts when not all selected', () => {
      const conflicts = [
        createMockConflict({ txHash: '0x111' }),
        createMockConflict({ txHash: '0x222' }),
        createMockConflict({ txHash: '0x333' }),
      ];

      composable.toggleAllOnPage(conflicts);

      expect(get(composable.selectedCount)).toBe(3);
      for (const c of conflicts)
        expect(composable.isSelected(c)).toBe(true);
    });

    it('deselects all page conflicts when all are selected', () => {
      const conflicts = [
        createMockConflict({ txHash: '0x111' }),
        createMockConflict({ txHash: '0x222' }),
      ];

      composable.toggleAllOnPage(conflicts);
      expect(get(composable.selectedCount)).toBe(2);

      composable.toggleAllOnPage(conflicts);
      expect(get(composable.selectedCount)).toBe(0);
    });

    it('preserves cross-page selections', () => {
      const page1 = [
        createMockConflict({ txHash: '0x111' }),
        createMockConflict({ txHash: '0x222' }),
      ];
      const page2 = [
        createMockConflict({ txHash: '0x333' }),
        createMockConflict({ txHash: '0x444' }),
      ];

      composable.toggleAllOnPage(page1);
      composable.toggleAllOnPage(page2);

      expect(get(composable.selectedCount)).toBe(4);

      composable.toggleAllOnPage(page1);
      expect(get(composable.selectedCount)).toBe(2);
      expect(composable.isSelected(page2[0])).toBe(true);
      expect(composable.isSelected(page2[1])).toBe(true);
    });
  });

  describe('areAllSelected', () => {
    it('returns false for empty page', () => {
      expect(composable.areAllSelected([])).toBe(false);
    });

    it('returns true when all page conflicts are selected', () => {
      const conflicts = [
        createMockConflict({ txHash: '0x111' }),
        createMockConflict({ txHash: '0x222' }),
      ];

      composable.toggleAllOnPage(conflicts);
      expect(composable.areAllSelected(conflicts)).toBe(true);
    });

    it('returns false when only some are selected', () => {
      const conflicts = [
        createMockConflict({ txHash: '0x111' }),
        createMockConflict({ txHash: '0x222' }),
      ];

      composable.toggleSelection(conflicts[0]);
      expect(composable.areAllSelected(conflicts)).toBe(false);
    });
  });

  describe('removeKeys', () => {
    it('removes specific keys from selection', () => {
      const c1 = createMockConflict({ txHash: '0x111' });
      const c2 = createMockConflict({ txHash: '0x222' });

      composable.toggleSelection(c1);
      composable.toggleSelection(c2);
      expect(get(composable.selectedCount)).toBe(2);

      composable.removeKeys(['ethereum:0x111']);
      expect(get(composable.selectedCount)).toBe(1);
      expect(composable.isSelected(c1)).toBe(false);
      expect(composable.isSelected(c2)).toBe(true);
    });
  });

  describe('selectedConflicts', () => {
    it('returns the full conflict objects', () => {
      const c1 = createMockConflict({ txHash: '0x111' });
      const c2 = createMockConflict({ chain: 'optimism', txHash: '0x222' });

      composable.toggleSelection(c1);
      composable.toggleSelection(c2);

      const selected = get(composable.selectedConflicts);
      expect(selected).toHaveLength(2);
      expect(selected).toEqual(expect.arrayContaining([c1, c2]));
    });
  });
});
