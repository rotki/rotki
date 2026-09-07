import type { Collection } from '@/modules/core/common/collection';
import type { AccountingRuleConflict } from '@/modules/settings/types/accounting';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref } from 'vue';
import { useAccountingRuleConflictResolution } from './use-accounting-rule-conflict-resolution';

interface TableState {
  collection?: Ref<Collection<AccountingRuleConflict>>;
}

const {
  getAccountingRulesConflicts,
  refetch,
  resolveAccountingRuleConflicts,
  setMessage,
  tableState,
} = vi.hoisted(() => {
  const tableState: TableState = {};
  return {
    getAccountingRulesConflicts: vi.fn(),
    refetch: vi.fn(async () => Promise.resolve()),
    resolveAccountingRuleConflicts: vi.fn(),
    setMessage: vi.fn(),
    tableState,
  };
});

vi.mock('@/modules/settings/accounting/use-accounting-settings', () => ({
  useAccountingSettings: (): Record<string, unknown> => ({
    getAccountingRulesConflicts,
    resolveAccountingRuleConflicts,
  }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  useServerTable: (): Record<string, unknown> => ({
    collection: tableState.collection,
    isLoading: ref<boolean>(false),
    pagination: ref({ limit: 10, page: 1, total: 0 }),
    refetch,
  }),
}));

function collection(total: number): Collection<AccountingRuleConflict> {
  return { data: [], found: total, limit: -1, total, totalValue: undefined };
}

let conflicts: Ref<Collection<AccountingRuleConflict>>;
let onResolved: ReturnType<typeof vi.fn<() => void>>;
let scope: ReturnType<typeof effectScope>;

function resolution(): ReturnType<typeof useAccountingRuleConflictResolution> {
  scope = effectScope();
  return scope.run(() => useAccountingRuleConflictResolution({ onResolved }))!;
}

describe('modules/settings/accounting/rule/useAccountingRuleConflictResolution', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    conflicts = ref<Collection<AccountingRuleConflict>>(collection(3));
    tableState.collection = conflicts;
    onResolved = vi.fn<() => void>();
    resolveAccountingRuleConflicts.mockResolvedValue({ success: true });
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('what is left to answer', () => {
    it('should start with every conflict unanswered', () => {
      const { remaining, resolutionLength } = resolution();

      expect(get(resolutionLength)).toBe(0);
      expect(get(remaining)).toBe(3);
    });

    it('should count down as conflicts are answered', () => {
      const { modelResolution, remaining } = resolution();
      set(modelResolution, { a: 'local', b: 'remote' });

      expect(get(remaining)).toBe(1);
    });
  });

  describe('what may be submitted', () => {
    it('should refuse a resolution with nothing chosen', () => {
      const { valid } = resolution();

      expect(get(valid)).toBe(false);
    });

    it('should accept one conflict answered individually', () => {
      const { modelResolution, valid } = resolution();
      set(modelResolution, { a: 'local' });

      expect(get(valid)).toBe(true);
    });

    it('should accept a resolve-everything strategy with nothing answered', () => {
      const { modelSolveAllUsing, valid } = resolution();
      set(modelSolveAllUsing, 'remote');

      expect(get(valid)).toBe(true);
    });
  });

  describe('submitting', () => {
    it('should send exactly the conflicts the user answered', async () => {
      const { modelResolution, save } = resolution();
      set(modelResolution, { a: 'local', b: 'remote' });
      await save();

      expect(resolveAccountingRuleConflicts).toHaveBeenCalledWith({
        conflicts: [
          { localId: 'a', solveUsing: 'local' },
          { localId: 'b', solveUsing: 'remote' },
        ],
      });
    });

    it('should send an empty list when nothing was answered', async () => {
      const { save } = resolution();
      await save();

      expect(resolveAccountingRuleConflicts).toHaveBeenCalledWith({ conflicts: [] });
    });

    it('should send the strategy alone, discarding the individual answers', async () => {
      const { modelResolution, modelSolveAllUsing, save } = resolution();
      set(modelResolution, { a: 'local' });
      set(modelSolveAllUsing, 'remote');
      await save();

      expect(resolveAccountingRuleConflicts).toHaveBeenCalledWith({ solveAllUsing: 'remote' });
    });

    it('should mark itself loading only while the submit is in flight', async () => {
      const { loading, save } = resolution();

      const pending = save();
      expect(get(loading)).toBe(true);

      await pending;
      expect(get(loading)).toBe(false);
    });

    it('should tell the caller once it succeeds', async () => {
      const { save } = resolution();
      await save();

      expect(onResolved).toHaveBeenCalledOnce();
      expect(setMessage).not.toHaveBeenCalled();
    });
  });

  describe('when submitting fails', () => {
    beforeEach(() => {
      resolveAccountingRuleConflicts.mockResolvedValue({ message: 'rule is gone', success: false });
    });

    it('should report the reason and leave the dialog open', async () => {
      const { save } = resolution();
      await save();

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ success: false }));
      expect(onResolved).not.toHaveBeenCalled();
    });

    it('should include the backend message in the report', async () => {
      const { save } = resolution();
      await save();

      expect(setMessage).toHaveBeenCalledWith(
        expect.objectContaining({ description: expect.stringContaining('rule is gone') }),
      );
    });

    it('should stop loading so the user can try again', async () => {
      const { loading, save } = resolution();
      await save();

      expect(get(loading)).toBe(false);
    });
  });
});
